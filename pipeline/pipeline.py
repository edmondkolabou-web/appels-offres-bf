"""
NetSync Gov — Orchestrateur principal du pipeline PDF
Coordonne les 6 étapes : watcher → extraction → parsing → normalisation → insertion → alertes.
"""
import logging
import time
from datetime import datetime, date
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from pipeline.config import config
from pipeline.models import Base, AppelOffre, PipelineLog
from pipeline.watcher import DGCMEFWatcher
from pipeline.parser import PDFExtractor, AORawParser, LLMFallbackParser
from pipeline.normalizer import AONormalizer
from pipeline.alerts import AlertEngine

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("netsync.pipeline")


# ── Base de données ────────────────────────────────────────────────────────────
engine = create_engine(
    config.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Session:
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


def init_db():
    """Crée les tables si elles n'existent pas (dev/test uniquement — utiliser Alembic en prod)."""
    Base.metadata.create_all(bind=engine)
    logger.info("Tables initialisées")


# ── Pipeline ───────────────────────────────────────────────────────────────────

class PipelineOrchestrator:
    """
    Orchestre le pipeline complet en 6 étapes.

    Étape 1 : Watcher — détecte et télécharge les nouveaux PDFs
    Étape 2 : Extraction — extrait le texte brut du PDF
    Étape 3 : Parsing — identifie et structure chaque AO
    Étape 4 : Normalisation — nettoie et valide les données
    Étape 5 : Insertion BDD — upsert en PostgreSQL + search_vector
    Étape 6 : Alertes — email et WhatsApp aux abonnés concernés
    """

    def __init__(self, db: Session):
        self.db = db
        self.extractor = PDFExtractor()
        self.raw_parser = AORawParser()
        self.llm_parser = LLMFallbackParser() if config.USE_LLM_FALLBACK else None

    def run(self) -> dict:
        """
        Lance le pipeline complet.

        Returns:
            Rapport d'exécution avec statistiques.
        """
        start_time = time.time()
        rapport = {
            "run_at": datetime.now().isoformat(),
            "pdfs_traites": 0,
            "ao_extraits": 0,
            "ao_inseres": 0,
            "ao_mis_a_jour": 0,
            "alertes_envoyees": 0,
            "erreurs": [],
        }

        logger.info("═" * 60)
        logger.info("PIPELINE NETSYNC GOV — DÉMARRAGE")
        logger.info("═" * 60)

        # ── Étape 1 : Watcher ─────────────────────────────────────────────────
        logger.info("Étape 1 : Surveillance DGCMEF")
        try:
            watcher = DGCMEFWatcher(self.db)
            nouveaux_pdfs = watcher.run()
        except Exception as e:
            logger.error(f"Erreur watcher : {e}")
            rapport["erreurs"].append(f"Watcher: {e}")
            nouveaux_pdfs = []

        if not nouveaux_pdfs:
            logger.info("Aucun nouveau PDF détecté — pipeline terminé")
            rapport["duree_sec"] = round(time.time() - start_time, 2)
            return rapport

        logger.info(f"{len(nouveaux_pdfs)} nouveau(x) PDF(s) à traiter")

        # ── Traitement de chaque PDF ───────────────────────────────────────────
        for numero, pdf_path in nouveaux_pdfs:
            try:
                self._process_pdf(numero, pdf_path, rapport)
            except Exception as e:
                logger.error(f"Erreur traitement PDF n°{numero} : {e}")
                rapport["erreurs"].append(f"PDF n°{numero}: {e}")
                self._log_pipeline(numero, "echec", 0, 0, str(pdf_path), [str(e)],
                                   int((time.time() - start_time) * 1000))

        # Commit final
        try:
            self.db.commit()
            logger.info("Commit BDD effectué")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erreur commit BDD : {e}")
            rapport["erreurs"].append(f"Commit: {e}")

        rapport["pdfs_traites"] = len(nouveaux_pdfs)
        rapport["duree_sec"] = round(time.time() - start_time, 2)

        logger.info("═" * 60)
        logger.info(f"PIPELINE TERMINÉ en {rapport['duree_sec']}s")
        logger.info(f"  PDFs traités : {rapport['pdfs_traites']}")
        logger.info(f"  AOs extraits : {rapport['ao_extraits']}")
        logger.info(f"  AOs insérés  : {rapport['ao_inseres']}")
        logger.info(f"  Alertes      : {rapport['alertes_envoyees']}")
        if rapport["erreurs"]:
            logger.warning(f"  Erreurs      : {len(rapport['erreurs'])}")
        logger.info("═" * 60)

        return rapport

    def _process_pdf(self, numero: int, pdf_path: Path, rapport: dict) -> None:
        """Traite un PDF individuel à travers les étapes 2-6."""
        pdf_start = time.time()
        ao_nouveaux_ids = []
        erreurs_pdf = []

        logger.info(f"── PDF n°{numero} : {pdf_path.name}")

        # ── Étape 2 : Extraction texte ─────────────────────────────────────────
        logger.info("  Étape 2 : Extraction texte brut")
        full_text = self.extractor.extract_text(pdf_path)
        if not full_text.strip():
            logger.error(f"  PDF vide ou illisible : {pdf_path}")
            self._log_pipeline(numero, "echec", 0, 0, str(pdf_path),
                               ["PDF vide ou illisible"],
                               int((time.time() - pdf_start) * 1000))
            return

        logger.info(f"  Texte extrait : {len(full_text):,} caractères")

        # ── Étape 3 : Parsing des blocs AO ────────────────────────────────────
        logger.info("  Étape 3 : Parsing des blocs AO")
        blocs = self.extractor.split_into_blocks(full_text)
        ao_raws = []

        date_publication = date.today()  # À affiner depuis le nom du fichier
        for i, bloc in enumerate(blocs):
            try:
                ao_raw = self.raw_parser.parse_block(bloc, date_publication)
                if ao_raw is None:
                    continue

                # Fallback LLM si confiance faible
                if ao_raw.confiance < 0.4 and self.llm_parser:
                    logger.debug(f"    Bloc {i+1} : confiance {ao_raw.confiance} < 0.4, fallback LLM")
                    llm_data = self.llm_parser.parse(bloc)
                    if llm_data:
                        # Enrichir l'AORaw avec les données LLM
                        ao_raw.titre = llm_data.get("titre") or ao_raw.titre
                        ao_raw.reference = llm_data.get("reference") or ao_raw.reference
                        ao_raw.autorite_contractante = (
                            llm_data.get("autorite_contractante") or ao_raw.autorite_contractante
                        )
                        ao_raw.type_procedure = llm_data.get("type_procedure") or ao_raw.type_procedure
                        ao_raw.secteur = llm_data.get("secteur") or ao_raw.secteur
                        if llm_data.get("date_cloture"):
                            try:
                                ao_raw.date_cloture = date.fromisoformat(llm_data["date_cloture"])
                            except (ValueError, TypeError):
                                pass
                        ao_raw.montant_estime = llm_data.get("montant_estime") or ao_raw.montant_estime

                ao_raws.append(ao_raw)
            except Exception as e:
                logger.warning(f"    Bloc {i+1} : erreur parsing — {e}")
                erreurs_pdf.append(f"Bloc {i+1}: {e}")

        logger.info(f"  {len(ao_raws)} AO parsés sur {len(blocs)} blocs")
        rapport["ao_extraits"] += len(ao_raws)

        # ── Étapes 4 & 5 : Normalisation + Insertion ──────────────────────────
        logger.info("  Étape 4-5 : Normalisation + Insertion BDD")
        normalizer = AONormalizer(self.db)
        ao_inseres = []

        for ao_raw in ao_raws:
            try:
                ao_model = normalizer.normalize(ao_raw, numero, str(pdf_path))
                if ao_model is None:
                    continue

                ao_final, is_new = normalizer.upsert(ao_model)
                if is_new:
                    ao_inseres.append(ao_final)
                    ao_nouveaux_ids.append(str(ao_final.id))
            except Exception as e:
                logger.warning(f"  Erreur normalisation/insertion AO : {e}")
                erreurs_pdf.append(f"Normalisation: {e}")

        stats = normalizer.get_stats()
        logger.info(f"  Résultat : +{stats['inseres']} insérés, "
                    f"{stats['mis_a_jour']} mis à jour, "
                    f"{stats['doublons']} doublons")

        rapport["ao_inseres"] += stats["inseres"]
        rapport["ao_mis_a_jour"] += stats.get("mis_a_jour", 0)

        # Flush pour avoir les IDs en BDD
        self.db.flush()

        # ── Étape 6 : Alertes ─────────────────────────────────────────────────
        if ao_inseres:
            logger.info(f"  Étape 6 : Envoi alertes pour {len(ao_inseres)} nouveaux AOs")
            alert_engine = AlertEngine(self.db)
            for ao in ao_inseres:
                try:
                    sent = alert_engine.process_new_ao(ao)
                    rapport["alertes_envoyees"] += sent
                except Exception as e:
                    logger.error(f"  Erreur alertes pour AO {ao.reference} : {e}")
                    erreurs_pdf.append(f"Alerte {ao.reference}: {e}")

        # ── Log pipeline ───────────────────────────────────────────────────────
        statut = "succes" if not erreurs_pdf else ("partiel" if ao_inseres else "echec")
        duree = int((time.time() - pdf_start) * 1000)
        self._log_pipeline(
            numero, statut, len(ao_raws), stats["inseres"],
            str(pdf_path), erreurs_pdf, duree
        )

    def _log_pipeline(
        self, numero: int, statut: str, ao_extraits: int,
        ao_nouveaux: int, pdf_url: str, erreurs: list, duree_ms: int
    ) -> None:
        """Enregistre le résultat du pipeline dans pipeline_logs."""
        try:
            existing = (
                self.db.query(PipelineLog)
                .filter(PipelineLog.numero_quotidien == numero)
                .first()
            )
            if existing:
                existing.statut = statut
                existing.nb_ao_extraits = ao_extraits
                existing.nb_ao_nouveaux = ao_nouveaux
                existing.erreur = erreurs
                existing.duree_secondes = duree_ms
            else:
                log = PipelineLog(
                    numero_quotidien=numero,
                    statut=statut,
                    nb_nb_nb_ao_extraits=ao_extraits,
                    nb_nb_nb_ao_nouveaux=ao_nouveaux,
                    erreur=erreurs,
                    pdf_url=pdf_url,
                    duree_secondes=duree_ms,
                )
                self.db.add(log)
            self.db.flush()
        except Exception as e:
            logger.error(f"Erreur log pipeline : {e}")


# ── Point d'entrée Celery ──────────────────────────────────────────────────────

from celery import Celery

celery_app = Celery(
    "netsync_gov",
    broker=config.REDIS_URL,
    backend=config.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Africa/Ouagadougou",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_max_retries=config.RETRY_MAX,
)

# Planification automatique
celery_app.conf.beat_schedule = {
    "pipeline-quotidien": {
        "task": "pipeline.run_pipeline",
        "schedule": config.CRON_SCHEDULE,  # "0 7 * * 1-5" = Lun-Ven 7h00
    },
    "rappels-j3": {
        "task": "pipeline.run_rappels_j3",
        "schedule": "0 7 * * 1-6",  # Tous les jours à 7h00
    },
}


@celery_app.task(name="pipeline.run_pipeline", bind=True, max_retries=3)
def run_pipeline(self) -> dict:
    """Tâche Celery : lance le pipeline complet."""
    db = get_db()
    try:
        orchestrator = PipelineOrchestrator(db)
        return orchestrator.run()
    except Exception as exc:
        logger.error(f"Pipeline échoué : {exc}")
        db.rollback()
        raise self.retry(exc=exc, countdown=config.RETRY_DELAY_SEC)
    finally:
        db.close()


@celery_app.task(name="pipeline.run_rappels_j3")
def run_rappels_j3() -> dict:
    """Tâche Celery : envoie les rappels J-3."""
    db = get_db()
    try:
        engine = AlertEngine(db)
        sent = engine.process_rappels_j3()
        db.commit()
        logger.info(f"Rappels J-3 : {sent} alertes envoyées")
        return {"rappels_envoyes": sent}
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur rappels J-3 : {e}")
        return {"erreur": str(e)}
    finally:
        db.close()


# ── Exécution directe (tests) ──────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    logging.getLogger().setLevel(logging.DEBUG)
    logger.info("Lancement pipeline en mode direct (test)")
    db = get_db()
    try:
        orchestrator = PipelineOrchestrator(db)
        rapport = orchestrator.run()
        print("\n=== RAPPORT ===")
        for k, v in rapport.items():
            print(f"  {k}: {v}")
    finally:
        db.close()
