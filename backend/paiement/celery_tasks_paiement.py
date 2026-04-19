"""
NetSync Gov — Tâches Celery liées aux paiements et abonnements.
"""
import logging
from datetime import date

from celery import Celery

logger = logging.getLogger("netsync.tasks.paiement")

# Import du celery_app depuis pipeline.py (shared)
from pipeline import celery_app, get_db


@celery_app.task(name="paiements.expire_subscriptions")
def task_expire_subscriptions() -> dict:
    """
    Rétrograde les abonnés dont le plan a expiré.
    Planifié : chaque nuit à 00h30.
    """
    db = get_db()
    try:
        from subscription_service import SubscriptionService
        service = SubscriptionService(db)
        count = service.expire_subscriptions()
        return {"expired": count, "date": date.today().isoformat()}
    finally:
        db.close()


@celery_app.task(name="paiements.reset_daily_counters")
def task_reset_daily_counters() -> dict:
    """
    Remet à zéro les compteurs quotidiens (Plan Gratuit).
    Planifié : chaque nuit à 00h00.
    """
    db = get_db()
    try:
        from subscription_service import SubscriptionService
        service = SubscriptionService(db)
        service.reset_daily_counters()
        return {"reset": True, "date": date.today().isoformat()}
    finally:
        db.close()


@celery_app.task(name="paiements.check_pending")
def task_check_pending_payments() -> dict:
    """
    Vérifie le statut des paiements 'pending' auprès de CinetPay.
    Utile pour les cas où le webhook n'est pas reçu (réseau, timeout).
    Planifié : toutes les 2 heures.
    """
    db = get_db()
    try:
        from models import Paiement
        from subscription_service import SubscriptionService

        service = SubscriptionService(db)
        pending = (
            db.query(Paiement)
            .filter(Paiement.statut == "pending")
            .limit(50)
            .all()
        )
        activated = 0
        for p in pending:
            result = service.check_and_activate(p.transaction_id)
            if result and result.statut == "success":
                activated += 1

        logger.info(f"Check pending : {len(pending)} vérifiés, {activated} activés")
        return {"checked": len(pending), "activated": activated}
    finally:
        db.close()


# Ajouter au beat_schedule existant
celery_app.conf.beat_schedule.update({
    "expire-subscriptions": {
        "task": "paiements.expire_subscriptions",
        "schedule": "30 0 * * *",    # 00h30 chaque nuit
    },
    "reset-daily-counters": {
        "task": "paiements.reset_daily_counters",
        "schedule": "0 0 * * *",     # 00h00 chaque nuit
    },
    "check-pending-payments": {
        "task": "paiements.check_pending",
        "schedule": "0 */2 * * *",   # Toutes les 2 heures
    },
})
