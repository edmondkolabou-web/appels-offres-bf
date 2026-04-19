"""
NetSync Gov Candidature — Tâches Celery
Alertes pièces expirantes + rappels clôture candidatures.
"""
import logging
from datetime import date, timedelta

from celery import Celery
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger("netsync.tasks.candidature")

from pipeline import celery_app, get_db


@celery_app.task(name="candidatures.alertes_pieces_expiration")
def alerter_pieces_expirantes() -> dict:
    """
    Chaque matin à 08h00.
    Envoie des alertes WhatsApp + email pour les pièces qui expirent
    dans 30, 15 ou 7 jours.
    """
    db = get_db()
    try:
        from alertes_netsync_gov.email_sender import ResendClient
        from alertes_netsync_gov.whatsapp import WhatsAppClient

        mailer = ResendClient()
        wa     = WhatsAppClient()

        for jours_seuil in [30, 15, 7]:
            date_seuil = date.today() + timedelta(days=jours_seuil)

            rows = db.execute(text("""
                SELECT p.*, a.email, a.whatsapp, a.prenom
                FROM pieces_administratives p
                JOIN abonnes a ON a.id = p.abonne_id
                WHERE p.date_expiration = :seuil
                  AND a.plan != 'gratuit'
                  AND a.actif = true
            """), {"seuil": date_seuil}).fetchall()

            for row in rows:
                # Email
                subject = f"[NetSync Gov] ⚠️ Pièce expirante dans {jours_seuil} jours — {row.type_piece.upper()}"
                html = f"""
                <p>Bonjour {row.prenom},</p>
                <p>Votre <strong>{row.type_piece.upper()}</strong> expire le
                <strong>{row.date_expiration.strftime('%d/%m/%Y')}</strong>
                (dans {jours_seuil} jours).</p>
                <p>Renouvelez-la avant qu'elle soit rejetée lors de votre prochaine candidature.</p>
                <p>→ <a href="https://gov.netsync.bf/pieces">Gérer mes pièces</a></p>
                <p><em>NetSync Gov</em></p>
                """
                mailer.send(row.email, subject, html,
                            tags=[{"name": "type", "value": "piece_expiration"}])

                # WhatsApp
                if row.whatsapp:
                    wa.send_text(
                        row.whatsapp,
                        f"⚠️ *NetSync Gov* — Pièce expirante\n\n"
                        f"Bonjour {row.prenom},\n\n"
                        f"Votre *{row.type_piece.upper()}* expire le "
                        f"{row.date_expiration.strftime('%d/%m/%Y')} "
                        f"(dans {jours_seuil} jours).\n\n"
                        f"Renouvelez-la dès maintenant :\n"
                        f"🔗 gov.netsync.bf/pieces"
                    )

        return {"status": "ok", "date": date.today().isoformat()}
    finally:
        db.close()


@celery_app.task(name="candidatures.rappels_cloture")
def rappels_cloture_candidatures() -> dict:
    """
    Chaque matin à 07h30 (après le pipeline AO).
    Pour chaque candidature en préparation, alerte si
    la clôture de l'AO est dans 7, 3 ou 1 jour.
    """
    db = get_db()
    try:
        from alertes_netsync_gov.email_sender import ResendClient
        from alertes_netsync_gov.whatsapp import WhatsAppClient

        mailer = ResendClient()
        wa     = WhatsAppClient()
        total  = 0

        for jours in [7, 3, 1]:
            cible = date.today() + timedelta(days=jours)

            rows = db.execute(text("""
                SELECT c.id, a.email, a.whatsapp, a.prenom,
                       ao.titre, ao.date_cloture, ao.autorite_contractante,
                       av.score_global
                FROM candidatures c
                JOIN abonnes a   ON a.id  = c.abonne_id
                JOIN appels_offres ao ON ao.id = c.ao_id
                LEFT JOIN LATERAL (
                    SELECT :score_placeholder AS score_global
                ) av ON true
                WHERE c.statut = 'en_preparation'
                  AND ao.date_cloture = :cible
                  AND a.plan != 'gratuit'
            """), {"cible": cible, "score_placeholder": 0}).fetchall()

            for row in rows:
                emoji = "🚨" if jours == 1 else "⏰"
                label = "DEMAIN" if jours == 1 else f"dans {jours} jours"

                # Email
                subject = f"[NetSync Gov] {emoji} Clôture {label} — {row.titre[:50]}"
                html = f"""
                <p>Bonjour {row.prenom},</p>
                <p>Votre candidature pour l'AO suivant clôture <strong>{label}</strong> :</p>
                <blockquote><strong>{row.titre}</strong><br>
                {row.autorite_contractante or ''}<br>
                Clôture : <strong>{row.date_cloture.strftime('%d/%m/%Y')}</strong></blockquote>
                <p>→ <a href="https://gov.netsync.bf/candidatures/{row.id}">Voir mon dossier</a></p>
                <p><em>NetSync Gov</em></p>
                """
                mailer.send(row.email, subject, html,
                            tags=[{"name": "type", "value": "rappel_cloture_candidature"}])

                # WhatsApp
                if row.whatsapp:
                    wa.send_text(
                        row.whatsapp,
                        f"{emoji} *NetSync Gov* — Rappel clôture {label}\n\n"
                        f"*{row.titre[:80]}*\n"
                        f"{row.autorite_contractante or ''}\n"
                        f"📅 Clôture : {row.date_cloture.strftime('%d/%m/%Y')}\n\n"
                        f"🔗 Voir mon dossier : gov.netsync.bf/candidatures/{row.id}"
                    )
                total += 1

        logger.info(f"Rappels clôture candidatures : {total} envoyés")
        return {"rappels_envoyes": total, "date": date.today().isoformat()}
    finally:
        db.close()


# Ajouter au beat_schedule
celery_app.conf.beat_schedule.update({
    "alertes-pieces-expiration": {
        "task":     "candidatures.alertes_pieces_expiration",
        "schedule": "0 8 * * 1-6",   # Lun-Sam à 08h00
    },
    "rappels-cloture-candidatures": {
        "task":     "candidatures.rappels_cloture",
        "schedule": "30 7 * * 1-6",  # Lun-Sam à 07h30
    },
})
