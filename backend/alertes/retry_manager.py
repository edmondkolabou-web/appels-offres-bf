"""
NetSync Gov — Gestionnaire de retry pour les envois échoués.
Relance les alertes échouées via une tâche Celery périodique.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.models import EnvoiAlerte, Abonne, AppelOffre

logger = logging.getLogger("netsync.retry")

MAX_TENTATIVES = 3
RETRY_INTERVAL_HOURS = 1


def get_failed_envois(db: Session, limit: int = 50) -> list[EnvoiAlerte]:
    """
    Retourne les envois en échec éligibles au retry :
    - statut = 'echec' ou 'reessai'
    - tentatives < MAX_TENTATIVES
    - dernière tentative il y a plus de RETRY_INTERVAL_HOURS
    """
    cutoff = datetime.utcnow() - timedelta(hours=RETRY_INTERVAL_HOURS)
    return (
        db.query(EnvoiAlerte)
        .filter(
            EnvoiAlerte.statut.in_(["echec", "reessai"]),
            EnvoiAlerte.tentatives < MAX_TENTATIVES,
            EnvoiAlerte.envoye_le < cutoff,
        )
        .limit(limit)
        .all()
    )


def process_retry(db: Session) -> dict:
    """
    Tâche principale de retry.
    Pour chaque envoi échoué éligible, réessaie selon le canal.
    """
    from whatsapp import AOAlertWhatsApp
    from email_sender import ResendClient
    from email_templates import render_nouvel_ao, render_rappel_j3
    from composables_alerts import build_ao_email_context

    failed = get_failed_envois(db)
    logger.info(f"Retry : {len(failed)} envoi(s) à relancer")

    stats = {"retried": 0, "success": 0, "still_failing": 0}

    for envoi in failed:
        abonne = db.get(Abonne, envoi.abonne_id)
        ao     = db.get(AppelOffre, envoi.ao_id)

        if not abonne or not ao:
            envoi.statut = "echec"
            envoi.erreur = "Abonné ou AO introuvable"
            db.flush()
            continue

        success = False
        envoi.tentatives += 1
        envoi.statut = "reessai"
        db.flush()

        try:
            if envoi.canal == "whatsapp" and abonne.whatsapp:
                wa = AOAlertWhatsApp()
                if envoi.type_alerte == "rappel_j3":
                    result = wa.send_rappel_j3(abonne, ao)
                else:
                    result = wa.send_nouvel_ao(abonne, ao)
                success = result.get("success", False)

            elif envoi.canal == "email":
                client = ResendClient()
                ctx = build_ao_email_context(ao)
                ao_url = f"https://gov.netsync.bf/aos/{ao.id}"
                if envoi.type_alerte == "rappel_j3":
                    subject, html = render_rappel_j3(
                        prenom=abonne.prenom, ao_titre=ao.titre,
                        ao_reference=ao.reference, autorite=ao.autorite_contractante or "",
                        date_cloture=ctx["date_cloture"], jours_restants=ao.jours_restants or 3,
                        ao_url=ao_url,
                    )
                else:
                    subject, html = render_nouvel_ao(
                        prenom=abonne.prenom, **ctx, ao_url=ao_url,
                        est_urgent=ao.est_urgent, jours_restants=ao.jours_restants,
                    )
                result = client.send(abonne.email, subject, html,
                                     tags=[{"name": "type", "value": envoi.type_alerte},
                                           {"name": "retry", "value": "true"}])
                success = result.get("success", False)

            if success:
                envoi.statut = "envoye"
                envoi.erreur = None
                stats["success"] += 1
                logger.info(f"Retry OK : envoi {envoi.id}")
            else:
                envoi.statut = "echec"
                stats["still_failing"] += 1

        except Exception as e:
            envoi.statut = "echec"
            envoi.erreur = str(e)
            stats["still_failing"] += 1
            logger.error(f"Retry exception pour envoi {envoi.id}: {e}")

        stats["retried"] += 1
        db.flush()

    db.commit()
    logger.info(f"Retry terminé : {stats}")
    return stats
