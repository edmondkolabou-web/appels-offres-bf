"""
NetSync Gov Transparence — Extension du parser pour les attributions
Ajoute la détection des blocs "Résultats d'attribution" dans le Quotidien DGCMEF.
À intégrer dans pipeline_netsync_gov/parser.py
"""
import re
import logging
from datetime import date
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger("netsync.parser.attributions")

MOIS_FR = {
    "janvier": 1, "février": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
    "janv": 1, "févr": 2, "avr": 4, "juil": 7, "sept": 9, "oct": 10, "nov": 11, "déc": 12,
}


@dataclass
class AttributionRaw:
    """Données brutes d'une attribution extraite du Quotidien DGCMEF."""
    reference:        Optional[str]
    titre:            Optional[str]
    attributaire:     Optional[str]
    montant_final:    Optional[int]
    date_signature:   Optional[date]
    source_quotidien: Optional[int]
    confiance:        float = 0.0


class AttributionParser:
    """
    Extrait les attributions de marché depuis les blocs texte du Quotidien DGCMEF.

    Formats détectés :
    - "RÉSULTATS D'ATTRIBUTION" ou "AVIS DE RÉSULTATS DE DÉPOUILLEMENT"
    - "Attributaire :", "Entreprise retenue :", "Soumissionnaire retenu :"
    - "Montant du marché :", "Montant TTC :", "Montant :"
    - "Date de signature :", "Date de notification :"
    """

    # Patterns de détection des blocs attribution
    BLOC_PATTERNS = [
        r"r[ée]sultats?\s+d[''']attribution",
        r"avis\s+de\s+r[ée]sultats?\s+de\s+d[ée]pouillement",
        r"attribution\s+d[ée]finitive",
        r"march[ée]\s+attribu[ée]",
        r"r[ée]sultat\s+d[ée]finitif",
    ]

    def is_attribution_block(self, text: str) -> bool:
        """Vérifie si un bloc contient des résultats d'attribution."""
        text_lower = text.lower()
        return any(re.search(p, text_lower) for p in self.BLOC_PATTERNS)

    def extract_reference(self, text: str) -> Optional[str]:
        """Extrait la référence de l'AO associé."""
        patterns = [
            r"[Nn]°\s*([\w/-]+/(?:AO|DPX|AMI|RFP|RFQ)[\w/-]*)",
            r"[Rr][ée]f[ée]rence\s*:?\s*([\w/-]+)",
            r"(20\d{2}-\d{3}/[\w/]+)",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.group(1).strip()
        return None

    def extract_attributaire(self, text: str) -> Optional[str]:
        """Extrait le nom de l'entreprise attributaire."""
        patterns = [
            r"[Aa]ttributaire\s*:?\s*([A-ZÀ-Ÿa-zà-ÿ][\w\s\-\'&\.]{5,80}?)(?:\n|$|;|,\s*[Mm]ontant)",
            r"[Ee]ntreprise\s+retenue?\s*:?\s*([A-ZÀ-Ÿ][\w\s\-\'&\.]{5,80}?)(?:\n|$|;)",
            r"[Ss]oumissionnaire\s+retenu?\s*:?\s*([A-ZÀ-Ÿ][\w\s\-\'&\.]{5,80}?)(?:\n|$|;)",
            r"[Aa]djudicataire\s*:?\s*([A-ZÀ-Ÿ][\w\s\-\'&\.]{5,80}?)(?:\n|$|;)",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                val = m.group(1).strip().rstrip(",;.")
                if len(val) >= 5:
                    return val
        return None

    def extract_montant(self, text: str) -> Optional[int]:
        """Extrait le montant final attribué en FCFA."""
        patterns = [
            r"[Mm]ontant\s+(?:du\s+march[ée]|TTC|final|d[''']attribution)\s*:?\s*([\d\s]+(?:[\d])?)\s*(?:F\s*CFA|FCFA|XOF|francs?)",
            r"[Mm]ontant\s*:?\s*([\d\s]+(?:[\d])?)\s*(?:F\s*CFA|FCFA|XOF)",
            r"([\d\s]+)\s*(?:F\s*CFA|FCFA|XOF)\s*TTC",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                montant_str = re.sub(r"\s", "", m.group(1))
                try:
                    val = int(montant_str)
                    if 100_000 <= val <= 500_000_000_000:
                        return val
                except ValueError:
                    continue
        return None

    def extract_date_signature(self, text: str) -> Optional[date]:
        """Extrait la date de signature du marché."""
        patterns = [
            # "15 mars 2026"
            r"(?:[Dd]ate\s+de\s+(?:signature|notification|contrat)\s*:?\s*)?(\d{1,2})\s+([a-zéûîàè]+\.?)\s+(\d{4})",
            # "2026-03-15"
            r"(\d{4})-(\d{2})-(\d{2})",
            # "15/03/2026"
            r"(\d{1,2})/(\d{2})/(\d{4})",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if not m:
                continue
            try:
                groups = m.groups()
                if len(groups) == 3:
                    g1, g2, g3 = groups
                    if g1.isdigit() and len(g1) == 4:
                        # Format YYYY-MM-DD
                        return date(int(g1), int(g2), int(g3))
                    elif "/" in m.group(0) or (g2.isdigit() and g3.isdigit()):
                        # Format DD/MM/YYYY
                        return date(int(g3), int(g2), int(g1))
                    else:
                        # Format "15 mars 2026"
                        mois_num = MOIS_FR.get(g2.lower().rstrip("."))
                        if mois_num:
                            return date(int(g3), mois_num, int(g1))
            except (ValueError, TypeError):
                continue
        return None

    def calculate_confiance(self, attr: AttributionRaw) -> float:
        """Score de confiance 0-1 basé sur les champs extraits."""
        score = 0.0
        if attr.attributaire:    score += 0.40
        if attr.montant_final:   score += 0.30
        if attr.date_signature:  score += 0.20
        if attr.reference:       score += 0.10
        return round(score, 2)

    def parse_block(self, text: str, numero_quotidien: Optional[int] = None) -> Optional[AttributionRaw]:
        """
        Parse un bloc texte et retourne une AttributionRaw si c'est une attribution.
        """
        if not self.is_attribution_block(text):
            return None

        attr = AttributionRaw(
            reference=        self.extract_reference(text),
            titre=            None,  # Sera récupéré via la référence en BDD
            attributaire=     self.extract_attributaire(text),
            montant_final=    self.extract_montant(text),
            date_signature=   self.extract_date_signature(text),
            source_quotidien= numero_quotidien,
        )
        attr.confiance = self.calculate_confiance(attr)

        # Rejeter si trop peu de confiance
        if attr.confiance < 0.40 or not attr.attributaire:
            logger.debug(f"Attribution rejetée (confiance={attr.confiance}, attributaire={attr.attributaire})")
            return None

        logger.info(f"Attribution détectée : {attr.attributaire} | {attr.montant_final} FCFA | confiance={attr.confiance}")
        return attr

    def parse_document(self, full_text: str, numero_quotidien: Optional[int] = None) -> list[AttributionRaw]:
        """
        Parse un document PDF complet et retourne toutes les attributions trouvées.
        """
        # Découper en blocs (même logique que le parser AO)
        blocs = re.split(
            r"(?=(?:R[ÉE]SULTATS?\s+D[''']ATTRIBUTION|AVIS\s+DE\s+R[ÉE]SULTATS?))",
            full_text,
            flags=re.IGNORECASE
        )

        attributions = []
        for bloc in blocs:
            if len(bloc.strip()) < 50:
                continue
            attr = self.parse_block(bloc, numero_quotidien)
            if attr:
                attributions.append(attr)

        logger.info(f"Quotidien N°{numero_quotidien} — {len(attributions)} attribution(s) extraite(s)")
        return attributions


# ── Normalisation et upsert en BDD ────────────────────────────────────────────

def upsert_attribution(attr: AttributionRaw, db) -> bool:
    """
    Insère ou met à jour une attribution en base PostgreSQL.
    Fait le lien avec l'AO source via la référence.
    """
    from sqlalchemy import text

    # Chercher l'AO associé via la référence
    ao_id = None
    if attr.reference:
        ao = db.execute(
            text("SELECT id FROM appels_offres WHERE reference ILIKE :ref LIMIT 1"),
            {"ref": f"%{attr.reference}%"}
        ).fetchone()
        if ao:
            ao_id = str(ao.id)

    # Vérifier doublon (même attributaire + même quotidien)
    existing = db.execute(
        text("""
            SELECT id FROM attributions
            WHERE attributaire ILIKE :attr
              AND source_quotidien = :src
        """),
        {"attr": attr.attributaire, "src": attr.source_quotidien}
    ).fetchone()

    if existing:
        logger.debug(f"Attribution déjà indexée : {attr.attributaire} (Q°{attr.source_quotidien})")
        return False

    db.execute(text("""
        INSERT INTO attributions
        (ao_id, attributaire, montant_final, date_signature, source_quotidien)
        VALUES (:ao_id, :attributaire, :montant, :date_sig, :src)
    """), {
        "ao_id":       ao_id,
        "attributaire": attr.attributaire,
        "montant":      attr.montant_final,
        "date_sig":     attr.date_signature,
        "src":          attr.source_quotidien,
    })
    db.flush()
    return True
