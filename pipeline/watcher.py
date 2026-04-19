"""
NetSync Gov — Étape 1 : Watcher DGCMEF
Détecte les nouveaux numéros du Quotidien des Marchés Publics et télécharge les PDFs.
"""
import re
import logging
import requests
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Tuple

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from config import config
from models import PipelineLog

logger = logging.getLogger("netsync.watcher")


class DGCMEFWatcher:
    """
    Surveille la page d'index DGCMEF et télécharge les nouveaux PDFs.

    Stratégie :
    1. Scrape la page d'index pour extraire les liens PDF récents.
    2. Identifie le numéro du Quotidien dans le nom de fichier ou l'URL.
    3. Compare avec le dernier numéro en base pour détecter les nouveautés.
    4. Télécharge et stocke le PDF localement.
    5. Logue le résultat dans pipeline_logs.
    """

    def __init__(self, db: Session):
        self.db = db
        self.session = requests.Session()
        self.session.headers.update(config.REQUEST_HEADERS)
        self.session.timeout = config.REQUEST_TIMEOUT
        Path(config.PDF_STORAGE_DIR).mkdir(parents=True, exist_ok=True)

    # ── Détection ──────────────────────────────────────────────────────────────

    def get_latest_quotidien_number(self) -> Optional[int]:
        """Retourne le dernier numéro de Quotidien connu en BDD."""
        row = (
            self.db.query(PipelineLog)
            .filter(PipelineLog.statut.in_(["succes", "partiel"]))
            .order_by(PipelineLog.numero_quotidien.desc())
            .first()
        )
        return row.numero_quotidien if row else None

    def scrape_index_page(self) -> list[dict]:
        """
        Scrape la page d'index DGCMEF et retourne les PDFs disponibles.

        Returns:
            Liste de dicts : [{"numero": int, "url": str, "date": str}, ...]
        """
        results = []
        try:
            resp = self.session.get(config.DGCMEF_INDEX_URL)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Échec scraping index DGCMEF : {e}")
            return results

        soup = BeautifulSoup(resp.text, "html.parser")

        # Chercher tous les liens PDF sur la page
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if not href.lower().endswith(".pdf"):
                continue

            # Construire l'URL complète
            if href.startswith("http"):
                pdf_url = href
            elif href.startswith("/"):
                pdf_url = config.DGCMEF_BASE_URL + href
            else:
                pdf_url = config.DGCMEF_BASE_URL + "/" + href

            # Extraire le numéro depuis l'URL ou le texte du lien
            numero = self._extract_numero(href) or self._extract_numero(link.get_text())
            if not numero:
                continue

            # Date approximative (texte adjacent ou date du jour)
            date_str = self._extract_date_from_context(link) or date.today().isoformat()

            results.append({
                "numero": numero,
                "url": pdf_url,
                "date": date_str,
            })

        # Dédupliquer et trier
        seen = set()
        unique = []
        for r in results:
            if r["numero"] not in seen:
                seen.add(r["numero"])
                unique.append(r)
        unique.sort(key=lambda x: x["numero"], reverse=True)

        logger.info(f"Index DGCMEF : {len(unique)} PDF(s) trouvé(s)")
        return unique

    def _extract_numero(self, text: str) -> Optional[int]:
        """Extrait le numéro du Quotidien depuis un texte ou une URL."""
        text = text or ""
        # Patterns courants : "Quotidien_N°714", "quotidien-714", "n4087"
        patterns = [
            r"[Qq]uotidien[_\s-]*[Nn]°?\s*(\d+)",
            r"[Qq]uotidien[_\s-]*(\d{3,4})",
            r"[Nn]°?\s*(\d{3,4})",
            r"[Nn](\d{4})",
            r"revue[_-](\d+)",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                num = int(m.group(1))
                if 100 <= num <= 9999:  # Sanity check
                    return num
        return None

    def _extract_date_from_context(self, link_tag) -> Optional[str]:
        """Essaie d'extraire une date depuis le texte entourant le lien."""
        ctx = link_tag.get_text() + " " + str(link_tag.parent or "")
        # Pattern date française : "27 mars 2026" ou "2026-03-27"
        mois = {
            "janvier": "01", "février": "02", "mars": "03", "avril": "04",
            "mai": "05", "juin": "06", "juillet": "07", "août": "08",
            "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12",
        }
        m = re.search(r"(\d{1,2})\s+(" + "|".join(mois) + r")\s+(\d{4})", ctx.lower())
        if m:
            j, mo, a = m.group(1), mois[m.group(2)], m.group(3)
            return f"{a}-{mo}-{j.zfill(2)}"
        m = re.search(r"(\d{4}-\d{2}-\d{2})", ctx)
        if m:
            return m.group(1)
        return None

    # ── Téléchargement ─────────────────────────────────────────────────────────

    def download_pdf(self, numero: int, url: str) -> Optional[Path]:
        """
        Télécharge un PDF et le sauvegarde localement.

        Returns:
            Path vers le fichier téléchargé, ou None si erreur.
        """
        # Dossier organisé par année/mois
        today = date.today()
        dest_dir = Path(config.PDF_STORAGE_DIR) / str(today.year) / f"{today.month:02d}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / f"quotidien_{numero:04d}.pdf"

        # Ne pas re-télécharger si déjà présent
        if dest_path.exists():
            logger.info(f"PDF n°{numero} déjà présent : {dest_path}")
            return dest_path

        logger.info(f"Téléchargement PDF n°{numero} depuis {url}")
        try:
            resp = self.session.get(url, stream=True, timeout=60)
            resp.raise_for_status()

            # Vérifier Content-Type
            ct = resp.headers.get("Content-Type", "")
            if "pdf" not in ct.lower() and "octet-stream" not in ct.lower():
                logger.warning(f"Content-Type inattendu pour n°{numero}: {ct}")

            # Écriture avec vérification de taille minimale
            total = 0
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    total += len(chunk)

            if total < 10_000:  # < 10 Ko → probablement pas un vrai PDF
                logger.error(f"PDF n°{numero} trop petit ({total} octets) — ignoré")
                dest_path.unlink(missing_ok=True)
                return None

            logger.info(f"PDF n°{numero} téléchargé : {total:,} octets → {dest_path}")
            return dest_path

        except requests.RequestException as e:
            logger.error(f"Erreur téléchargement PDF n°{numero} : {e}")
            dest_path.unlink(missing_ok=True)
            return None

    # ── Orchestration ──────────────────────────────────────────────────────────

    def run(self) -> list[Tuple[int, Path]]:
        """
        Point d'entrée principal du watcher.

        Returns:
            Liste de (numero, pdf_path) pour les nouveaux PDFs téléchargés.
        """
        logger.info("=== Watcher DGCMEF démarré ===")
        derniere_connue = self.get_latest_quotidien_number() or 0
        logger.info(f"Dernier numéro connu en BDD : {derniere_connue}")

        pdf_list = self.scrape_index_page()
        if not pdf_list:
            logger.warning("Aucun PDF trouvé sur la page d'index DGCMEF")
            return []

        nouveaux = []
        for item in pdf_list:
            if item["numero"] <= derniere_connue:
                continue  # Déjà traité

            logger.info(f"Nouveau Quotidien détecté : n°{item['numero']}")
            path = self.download_pdf(item["numero"], item["url"])
            if path:
                nouveaux.append((item["numero"], path, item["url"]))

        logger.info(f"Watcher terminé : {len(nouveaux)} nouveau(x) PDF(s)")
        return [(n, p) for n, p, _ in nouveaux]
