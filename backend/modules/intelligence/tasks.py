"""
NetSync Gov Intelligence — Génération automatique du rapport mensuel
Tâche Celery : le 1er de chaque mois à 06h00, générer et envoyer le rapport.
"""
import logging
from datetime import date

logger = logging.getLogger("netsync.rapport")

from pipeline import celery_app, get_db


@celery_app.task(name="intelligence.rapport_mensuel_auto")
def generer_rapport_mensuel_auto() -> dict:
    """
    Génère et envoie le rapport mensuel à tous les abonnés Pro.
    Planifié : 1er de chaque mois à 06h00.
    """
    db = get_db()
    try:
        from alertes_netsync_gov.email_sender import ResendClient
        from sqlalchemy import text

        mailer = ResendClient()

        # Récupérer tous les abonnés Pro actifs
        abonnes = db.execute(text("""
            SELECT id, email, prenom FROM abonnes
            WHERE plan IN ('pro', 'equipe') AND actif = true
        """)).fetchall()

        # Générer le PDF du mois dernier
        mois_dernier = date.today().replace(day=1)
        import calendar
        if mois_dernier.month == 1:
            mois_rapport = mois_dernier.replace(year=mois_dernier.year - 1, month=12)
        else:
            mois_rapport = mois_dernier.replace(month=mois_dernier.month - 1)

        logger.info(f"Génération rapport {mois_rapport.strftime('%B %Y')} pour {len(abonnes)} abonnés")

        # Pour chaque abonné, envoyer par email avec lien de téléchargement
        sent = 0
        for ab in abonnes:
            try:
                subject = f"[NetSync Gov] Rapport mensuel — Commande publique BF · {mois_rapport.strftime('%B %Y').capitalize()}"
                html = f"""
                <p>Bonjour {ab.prenom},</p>
                <p>Votre rapport mensuel sur la commande publique burkinabè est disponible.</p>
                <p>Il couvre l'activité des appels d'offres publics du Burkina Faso
                pour le mois de <strong>{mois_rapport.strftime('%B %Y').capitalize()}</strong>.</p>
                <p>
                  <a href="https://gov.netsync.bf/intelligence/rapport?mois={mois_rapport.strftime('%Y-%m')}"
                     style="display:inline-block;background:#0082C9;color:white;padding:10px 20px;
                            border-radius:8px;text-decoration:none;font-weight:500;">
                    Télécharger le rapport PDF →
                  </a>
                </p>
                <p style="font-size:12px;color:#64748B;">
                  Le rapport contient : volume d'AOs par secteur, top autorités contractantes,
                  tendances, analyse IA du marché.
                </p>
                <p><em>NetSync Gov</em></p>
                """
                mailer.send(
                    ab.email, subject, html,
                    tags=[{"name": "type", "value": "rapport_mensuel"}]
                )
                sent += 1
            except Exception as e:
                logger.error(f"Erreur envoi rapport à {ab.email}: {e}")

        logger.info(f"Rapport mensuel envoyé à {sent}/{len(abonnes)} abonnés")
        return {"mois": mois_rapport.isoformat(), "envoyes": sent, "total": len(abonnes)}

    finally:
        db.close()


# Ajouter au beat_schedule
celery_app.conf.beat_schedule.update({
    "rapport-mensuel-auto": {
        "task":     "intelligence.rapport_mensuel_auto",
        "schedule": "0 6 1 * *",  # Le 1er de chaque mois à 06h00
    },
})
