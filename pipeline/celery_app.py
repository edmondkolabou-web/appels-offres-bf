"""
NetSync Gov — Celery App + Beat Scheduler
Tâches automatisées :
- Pipeline quotidien à 07h00 (lun-ven)
- Mise à jour statuts AOs (clôturés) à minuit
- Relance abonnements expirés à 08h00
"""
import os
import logging
from datetime import datetime

from celery import Celery
from celery.schedules import crontab

# Config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ── Celery App ─────────────────────────────────────────────────────────────────
app = Celery(
    "netsync_gov",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Africa/Ouagadougou",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=86400,  # 24h
)

# ── Beat Schedule ──────────────────────────────────────────────────────────────
app.conf.beat_schedule = {
    # Pipeline principal : 07h00 du lundi au vendredi
    "pipeline-quotidien-07h00": {
        "task": "pipeline.celery_app.run_pipeline",
        "schedule": crontab(hour=7, minute=0, day_of_week="1-5"),
        "args": (),
        "options": {"queue": "pipeline"},
    },

    # Vérification supplémentaire : 12h00 (au cas où le PDF sort en retard)
    "pipeline-midi-12h00": {
        "task": "pipeline.celery_app.run_pipeline",
        "schedule": crontab(hour=12, minute=0, day_of_week="1-5"),
        "args": (),
        "options": {"queue": "pipeline"},
    },

    # Mise à jour statuts : minuit chaque jour
    "update-statuts-minuit": {
        "task": "pipeline.celery_app.update_ao_statuts",
        "schedule": crontab(hour=0, minute=0),
        "args": (),
    },

    # Alertes J-3 : 07h30 chaque jour
    "alertes-j3-07h30": {
        "task": "pipeline.celery_app.send_j3_alerts",
        "schedule": crontab(hour=7, minute=30, day_of_week="1-5"),
        "args": (),
    },

    # Relance abonnements expirés : 08h00
    "relance-abonnements": {
        "task": "pipeline.celery_app.check_expired_subscriptions",
        "schedule": crontab(hour=8, minute=0),
        "args": (),
    },
}

logger = logging.getLogger("netsync.celery")


# ── Tâches ─────────────────────────────────────────────────────────────────────
@app.task(bind=True, max_retries=3, default_retry_delay=300)
def run_pipeline(self):
    """Tâche Celery : lance le pipeline complet."""
    logger.info("Tâche Celery: pipeline démarré")

    try:
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        os.environ.setdefault("DATABASE_URL", REDIS_URL.replace("/0", "").replace("redis", "postgresql").replace("6379", "5432"))

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        db_url = os.getenv("DATABASE_URL", "postgresql://netsync:devpassword@localhost:5432/netsync_gov_dev")
        engine = create_engine(db_url, pool_pre_ping=True)
        Session = sessionmaker(bind=engine)
        db = Session()

        from pipeline import PipelineOrchestrator
        orchestrator = PipelineOrchestrator(db)
        rapport = orchestrator.run()

        db.close()

        logger.info(f"Pipeline terminé: {rapport.get('ao_inseres', 0)} AOs insérés")
        return rapport

    except Exception as exc:
        logger.error(f"Pipeline échoué: {exc}")
        raise self.retry(exc=exc)


@app.task
def update_ao_statuts():
    """Met à jour les statuts des AOs : ouvert → clôturé si date_cloture dépassée."""
    from datetime import date
    from sqlalchemy import create_engine, update
    from sqlalchemy.orm import sessionmaker

    db_url = os.getenv("DATABASE_URL", "postgresql://netsync:devpassword@localhost:5432/netsync_gov_dev")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from models import AppelOffre

        result = db.execute(
            update(AppelOffre)
            .where(AppelOffre.statut == "ouvert")
            .where(AppelOffre.date_cloture < date.today())
            .values(statut="cloture")
        )
        db.commit()
        count = result.rowcount
        logger.info(f"Statuts mis à jour: {count} AO(s) clôturé(s)")
        return {"updated": count}
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur mise à jour statuts: {e}")
        return {"error": str(e)}
    finally:
        db.close()


@app.task
def send_j3_alerts():
    """Envoie des alertes pour les AOs qui clôturent dans 3 jours."""
    from datetime import date, timedelta
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_url = os.getenv("DATABASE_URL", "postgresql://netsync:devpassword@localhost:5432/netsync_gov_dev")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from models import AppelOffre

        j3 = date.today() + timedelta(days=3)
        aos_j3 = db.query(AppelOffre).filter(
            AppelOffre.statut == "ouvert",
            AppelOffre.date_cloture == j3,
        ).all()

        logger.info(f"Alertes J-3: {len(aos_j3)} AO(s) clôturent dans 3 jours")

        # TODO: Envoyer les alertes via le moteur d'alertes
        # from alerts import AlertEngine
        # alert_engine = AlertEngine(db)
        # alert_engine.send_j3_alerts(aos_j3)

        return {"aos_j3": len(aos_j3)}
    except Exception as e:
        logger.error(f"Erreur alertes J-3: {e}")
        return {"error": str(e)}
    finally:
        db.close()


@app.task
def check_expired_subscriptions():
    """Vérifie et suspend les abonnements expirés."""
    from datetime import date
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_url = os.getenv("DATABASE_URL", "postgresql://netsync:devpassword@localhost:5432/netsync_gov_dev")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from models import Abonne

        expired = db.query(Abonne).filter(
            Abonne.plan.in_(["pro", "equipe"]),
            Abonne.plan_expire_le < date.today(),
        ).all()

        for abonne in expired:
            abonne.plan = "gratuit"
            logger.info(f"Abonnement expiré: {abonne.email} → gratuit")

        db.commit()
        return {"expired": len(expired)}
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur check abonnements: {e}")
        return {"error": str(e)}
    finally:
        db.close()


# ── Lancement direct (test) ────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Tâches Celery NetSync Gov enregistrées:")
    for name, config_entry in app.conf.beat_schedule.items():
        print(f"  {name}: {config_entry['schedule']}")
    print()
    print("Lancer le worker: celery -A pipeline.celery_app worker -l info")
    print("Lancer le beat:   celery -A pipeline.celery_app beat -l info")
