"""
NetSync Gov — Étape 4 : Normalisation et déduplication
Nettoie, normalise et insère les AOs en base PostgreSQL.
"""
import logging
import re
import uuid
from datetime import date, datetime
from typing import Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from pipeline.models import AppelOffre
from pipeline.parser import AORaw
from pipeline.config import config

logger = logging.getLogger("netsync.normalizer")


class AONormalizer:
    """
    Étape 4 : Normalisation des données brutes avant insertion.

    Responsabilités :
    - Nettoyer les chaînes (espaces, caractères spéciaux)
    - Valider les types et contraintes
    - Générer une référence si manquante
    - Détecter les doublons via la référence
    - Insérer ou mettre à jour en base
    """

    def __init__(self, db: Session):
        self.db = db
        self._stats = {"inseres": 0, "mis_a_jour": 0, "doublons": 0, "rejetes": 0}

    # ── Normalisation ──────────────────────────────────────────────────────────

    def normalize(self, ao_raw: AORaw, numero_quotidien: int, pdf_url: str) -> Optional[AppelOffre]:
        """
        Normalise un AORaw et retourne un objet AppelOffre prêt pour l'insertion.

        Returns:
            AppelOffre normalisé, ou None si rejeté.
        """
        # Validation minimale
        if not ao_raw.titre or len(ao_raw.titre.strip()) < 15:
            logger.debug("AO rejeté : titre trop court")
            self._stats["rejetes"] += 1
            return None

        ao = AppelOffre()

        # Titre — nettoyage
        ao.titre = self._clean_text(ao_raw.titre, max_len=500)

        # Description = texte brut nettoyé (sans le titre)
        desc = ao_raw.texte_brut.replace(ao_raw.titre, "").strip()
        ao.description = self._clean_text(desc, max_len=5000) or None

        # Référence — générer si manquante
        ao.reference = self._normalize_reference(ao_raw.reference, ao_raw, numero_quotidien)

        # Autorité contractante
        ao.autorite_contractante = self._clean_text(
            ao_raw.autorite_contractante or "Non précisée", max_len=200
        )

        # Type procédure — validation enum
        ao.type_procedure = self._validate_enum(
            ao_raw.type_procedure, config.TYPES_PROCEDURE, default="ouvert"
        )

        # Secteur — validation enum
        ao.secteur = self._validate_enum(
            ao_raw.secteur, config.SECTEURS, default="autre"
        )

        # Statut — déterminé par date_cloture
        ao.statut = self._compute_statut(ao_raw.date_cloture)

        # Dates
        ao.date_publication = ao_raw.date_publication or date.today()
        ao.date_cloture = ao_raw.date_cloture

        # Montant
        ao.montant_estime = ao_raw.montant_estime

        # Source et métadonnées pipeline
        ao.source = ao_raw.source or "dgcmef"
        ao.pdf_url = pdf_url
        ao.numero_quotidien = numero_quotidien

        return ao

    def _clean_text(self, text: str, max_len: int = 500) -> str:
        """Nettoie un texte : espaces multiples, caractères de contrôle, longueur."""
        if not text:
            return ""
        # Supprimer caractères de contrôle sauf \n
        text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)
        # Normaliser espaces et sauts de ligne
        text = re.sub(r"\s+", " ", text)
        # Supprimer guillemets exotiques
        text = text.replace("\u2019", "'").replace("\u2018", "'")
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        return text.strip()[:max_len]

    def _normalize_reference(
        self, ref: Optional[str], ao: AORaw, numero_quotidien: int
    ) -> str:
        """
        Normalise la référence.
        Si absente, génère une référence déterministe depuis le contenu de l'AO.
        """
        if ref and len(ref.strip()) >= 5:
            # Nettoyer les espaces
            return re.sub(r"\s+", "", ref.strip())[:100]

        # Générer une référence synthétique reproductible
        # Format : NETSYNC-{quotidien}-{hash5du_titre}
        titre_hash = str(uuid.uuid5(
            uuid.NAMESPACE_DNS,
            f"{numero_quotidien}:{ao.titre[:100]}"
        ))[:8].upper()
        return f"NETSYNC-{numero_quotidien:04d}-{titre_hash}"

    def _validate_enum(self, value: Optional[str], valid: list, default: str) -> str:
        """Valide qu'une valeur est dans une liste, retourne le défaut sinon."""
        if value and value.lower() in valid:
            return value.lower()
        return default

    def _compute_statut(self, date_cloture: Optional[date]) -> str:
        """Détermine le statut en fonction de la date de clôture."""
        if not date_cloture:
            return "ouvert"
        if date_cloture < date.today():
            return "cloture"
        return "ouvert"

    # ── Déduplication et insertion ─────────────────────────────────────────────

    def upsert(self, ao: AppelOffre) -> Tuple[AppelOffre, bool]:
        """
        Insère un AO ou met à jour s'il existe déjà (basé sur la référence).

        Returns:
            (ao, is_new) — is_new = True si insertion, False si mise à jour.
        """
        existing = (
            self.db.query(AppelOffre)
            .filter(AppelOffre.reference == ao.reference)
            .first()
        )

        if existing:
            # Mise à jour des champs qui peuvent changer
            changed = False
            if existing.statut != ao.statut:
                existing.statut = ao.statut
                changed = True
            if ao.date_cloture and existing.date_cloture != ao.date_cloture:
                existing.date_cloture = ao.date_cloture
                changed = True
            if ao.montant_estime and not existing.montant_estime:
                existing.montant_estime = ao.montant_estime
                changed = True
            if changed:
                existing.updated_at = datetime.now()
                self._stats["mis_a_jour"] += 1
                logger.debug(f"AO mis à jour : {existing.reference}")
            else:
                self._stats["doublons"] += 1
                logger.debug(f"AO doublon ignoré : {existing.reference}")
            return existing, False

        # Nouveau AO
        try:
            self.db.add(ao)
            self.db.flush()  # Obtenir l'ID sans commit
            self._stats["inseres"] += 1
            logger.debug(f"AO inséré : {ao.reference}")
            return ao, True
        except IntegrityError as e:
            self.db.rollback()
            logger.warning(f"Contrainte violation pour {ao.reference} : {e}")
            self._stats["doublons"] += 1
            return ao, False

    def update_search_vectors(self, ao_ids: list) -> None:
        """
        Déclenche la mise à jour du search_vector via la fonction PostgreSQL.
        (Le trigger gère cela automatiquement à l'insert, mais utile pour les updates.)
        """
        if not ao_ids:
            return
        try:
            self.db.execute(
                text("""
                    UPDATE appels_offres
                    SET search_vector = to_tsvector('french',
                        coalesce(titre, '') || ' ' ||
                        coalesce(description, '') || ' ' ||
                        coalesce(autorite_contractante, '')
                    )
                    WHERE id = ANY(:ids)
                """),
                {"ids": ao_ids}
            )
        except Exception as e:
            logger.error(f"Erreur mise à jour search_vectors : {e}")

    def get_stats(self) -> dict:
        """Retourne les statistiques de traitement."""
        return dict(self._stats)
