"""
NetSync Gov — Étape 2 & 3 : Parser PDF DGCMEF
Extrait le texte brut puis structure chaque AO en champs normalisés.
"""
import re
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional, List

import pdfplumber
import dateparser

from config import config

logger = logging.getLogger("netsync.parser")


@dataclass
class AORaw:
    """Structure intermédiaire d'un AO extrait du PDF avant normalisation."""
    titre:                str = ""
    reference:            Optional[str] = None
    autorite_contractante: Optional[str] = None
    type_procedure:       Optional[str] = None
    secteur:              Optional[str] = None
    date_publication:     Optional[date] = None
    date_cloture:         Optional[date] = None
    montant_estime:       Optional[int] = None
    source:               str = "dgcmef"
    texte_brut:           str = ""
    confiance:            float = 0.0  # Score 0-1 de confiance du parsing


class PDFExtractor:
    """
    Étape 2 : Extraction du texte brut depuis le PDF.
    Utilise pdfplumber pour conserver la structure spatiale.
    """

    def extract_text(self, pdf_path: Path) -> str:
        """
        Extrait le texte complet du PDF page par page.

        Returns:
            Texte brut concaténé de toutes les pages.
        """
        full_text = []
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                logger.info(f"PDF ouvert : {len(pdf.pages)} page(s)")
                for i, page in enumerate(pdf.pages):
                    try:
                        text = page.extract_text(
                            x_tolerance=3,
                            y_tolerance=3,
                            layout=True,
                        ) or ""
                        full_text.append(f"\n--- PAGE {i+1} ---\n{text}")
                    except Exception as e:
                        logger.warning(f"Erreur extraction page {i+1} : {e}")
                        continue
        except Exception as e:
            logger.error(f"Impossible d'ouvrir le PDF {pdf_path} : {e}")
            return ""

        return "\n".join(full_text)

    def extract_tables(self, pdf_path: Path) -> List[List[List[str]]]:
        """
        Extrait les tableaux du PDF (utile pour les montants et références).

        Returns:
            Liste de tableaux, chaque tableau étant une liste de lignes.
        """
        tables = []
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                for page in pdf.pages:
                    page_tables = page.extract_tables() or []
                    tables.extend(page_tables)
        except Exception as e:
            logger.error(f"Erreur extraction tableaux : {e}")
        return tables

    def split_into_blocks(self, full_text: str) -> List[str]:
        """
        Découpe le texte brut en blocs correspondant à chaque AO.
        Adapté au format réel du Quotidien DGCMEF extrait par pdfplumber.
        """
        pages = re.split(r'--- PAGE \d+ ---', full_text)

        blocks = []

        for page_text in pages:
            if not page_text or len(page_text.strip()) < 50:
                continue

            # Nettoyer les espaces excessifs du mode layout
            lines = page_text.split('\n')
            cleaned_lines = []
            for line in lines:
                cleaned = re.sub(r'\s{3,}', '  ', line).strip()
                if cleaned:
                    cleaned_lines.append(cleaned)

            page_clean = '\n'.join(cleaned_lines)

            # Marqueurs d'un AO dans le Quotidien DGCMEF
            ao_markers = [
                r'Avis\s+de\s+demande\s+de\s+prix',
                r'Avis\s+d[\'\u2019]appel\s+d[\'\u2019]offres',
                r'Avis\s+de\s+manifestation',
                r'Avis\s+de\s+s[eé]lection',
                r'Avis\s+de\s+recrutement',
                r'Avis\s+de\s+sollicitation',
                r'Demande\s+de\s+propositions?',
                r'Request\s+for\s+(?:proposal|quotation)',
                r'Rectificatif\s+du\s+quotidien',
            ]

            combined = '|'.join(ao_markers)
            positions = [(m.start(), m.group()) for m in re.finditer(combined, page_clean, re.IGNORECASE)]

            if not positions:
                continue

            for idx, (pos, marker) in enumerate(positions):
                context_start = max(0, pos - 500)
                if idx + 1 < len(positions):
                    end_pos = positions[idx + 1][0]
                else:
                    end_pos = len(page_clean)

                block = page_clean[context_start:end_pos].strip()
                if len(block) > 100:
                    blocks.append(block)

        logger.info(f"Découpage : {len(blocks)} bloc(s) AO identifié(s)")
        return blocks if blocks else [full_text]

class AORawParser:
    """
    Étape 3 : Extraction des champs structurés depuis chaque bloc de texte.
    Utilise des regex + heuristiques. Fallback LLM pour les cas ambigus.
    """

    # ── Patterns regex ─────────────────────────────────────────────────────────

    REF_PATTERNS = [
        r"N°\s*([\d]{4}-[\d]+/[A-Z/]+(?:/[A-Z]+)*)",
        r"Réf[éeèê]rence\s*:?\s*([\w/-]+)",
        r"(BF-[\w-]+-\d+-(?:GO|CS|CW|IC)-\w+)",  # Format Banque Mondiale STEP
        r"(UNDP-\w+-\d+)",                          # Format UNDP
        r"N°\s*(\d{4}[-_]\d+[/\w]*)",
    ]

    DATE_PATTERNS = [
        r"(?:date\s+limite|cl[oô]ture|d[eé]p[oô]t|soumission)\s*:?\s*"
        r"(?:le\s+)?(\d{1,2}[\s/.-]\w+[\s/.-]\d{4})",
        r"(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|"
        r"août|septembre|octobre|novembre|décembre)\s+(\d{4})",
        r"(\d{2}/\d{2}/\d{4})",
        r"(\d{4}-\d{2}-\d{2})",
    ]

    MONTANT_PATTERNS = [
        r"(\d[\d\s]*(?:\.\d+)?)\s*(?:F\s*CFA|FCFA|XOF|francs\s+CFA)",
        r"montant\s*:?\s*([\d\s]+(?:\.\d+)?)",
    ]

    TYPE_KEYWORDS = {
        "ouvert": ["appel d'offres ouvert", "aoo", "appel d'offres international",
                   "appel d'offres national"],
        "restreint": ["appel d'offres restreint", "aor"],
        "dpx": ["demande de prix", "cotation"],
        "ami": ["manifestation d'intérêt", "ami"],
        "rfp": ["request for proposal", "rfp", "demande de propositions"],
        "rfq": ["request for quotation", "rfq", "demande de cotation"],
    }

    SECTEUR_KEYWORDS = {
        "informatique": ["informatique", "télécom", "réseau", "logiciel", "équipement it",
                         "matériel informatique", "système information", "numérique",
                         "technologie", "internet", "serveur", "ordinateur"],
        "btp": ["construction", "bâtiment", "travaux", "génie civil", "réhabilitation",
                "infrastructure", "route", "pont", "drainage", "forages", "hydraulique"],
        "sante": ["santé", "médical", "médicament", "pharmacie", "hôpital",
                  "laboratoire", "clinique", "chirurgie", "vaccin"],
        "agriculture": ["agriculture", "élevage", "semence", "intrant", "irrigation",
                        "pastoral", "agropastoral", "pisciculture", "maraîchage"],
        "conseil": ["consultant", "bureau d'étude", "expertise", "audit", "mission",
                    "assistance technique", "formation", "étude", "évaluation"],
        "equipement": ["équipement", "fourniture", "matériel", "mobilier",
                       "véhicule", "engin", "groupes électrogènes"],
        "transport": ["transport", "logistique", "camion", "fret"],
        "energie": ["énergie", "électricité", "solaire", "photovoltaïque",
                    "groupe électrogène", "biomasse"],
        "education": ["éducation", "école", "université", "enseignement", "salle de classe"],
        "securite": ["sécurité", "gardiennage", "surveillance", "militaire"],
    }

    def parse_block(self, bloc: str, date_publication: Optional[date] = None) -> Optional[AORaw]:
        """
        Parse un bloc de texte pour en extraire les champs d'un AO.

        Returns:
            AORaw si des champs suffisants sont extraits, None sinon.
        """
        if len(bloc.strip()) < 80:
            return None

        ao = AORaw()
        ao.texte_brut = bloc
        ao.date_publication = date_publication or date.today()
        ao.source = "dgcmef"

        # 1. Titre = premières lignes significatives
        ao.titre = self._extract_titre(bloc)
        if not ao.titre:
            return None

        # 2. Référence
        ao.reference = self._extract_reference(bloc)

        # 3. Autorité contractante
        ao.autorite_contractante = self._extract_autorite(bloc)

        # 4. Type de procédure
        ao.type_procedure = self._detect_type_procedure(bloc)

        # 5. Secteur
        ao.secteur = self._detect_secteur(bloc)

        # 6. Date de clôture
        ao.date_cloture = self._extract_date_cloture(bloc)

        # 7. Montant estimé
        ao.montant_estime = self._extract_montant(bloc)

        # Calcul score de confiance
        ao.confiance = self._compute_confidence(ao)

        return ao

    def _extract_titre(self, text: str) -> str:
        """Extrait le titre = premières lignes non vides en majuscules ou ligne significative."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        titre_parts = []
        for line in lines[:8]:  # Chercher dans les 8 premières lignes
            if len(line) < 10:
                continue
            titre_parts.append(line)
            # Arrêter après 2-3 lignes de titre
            if len(titre_parts) >= 2 and len(" ".join(titre_parts)) > 60:
                break
        titre = " ".join(titre_parts)
        # Nettoyer
        titre = re.sub(r"\s+", " ", titre).strip()
        # Limiter la longueur
        return titre[:400] if titre else ""

    def _extract_reference(self, text: str) -> Optional[str]:
        """Extrait la référence officielle du marché."""
        for pattern in self.REF_PATTERNS:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                ref = m.group(1).strip()
                if len(ref) >= 5:
                    return ref
        return None

    def _extract_autorite(self, text: str) -> Optional[str]:
        """Extrait l'autorité contractante."""
        patterns = [
            r"(?:maître\s+d['']ouvrage|autorit[eé]\s+contractante|organisme)\s*:?\s*([^\n]{5,80})",
            r"(?:au\s+profit\s+de|pour\s+le\s+compte\s+de)\s+([^\n]{5,80})",
            r"(?:minist[eèé]re|direction|agence|office|soci[eé]t[eé]|projet)\s+[^\n]{3,80}",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                val = m.group(1) if m.lastindex else m.group(0)
                val = re.sub(r"\s+", " ", val).strip()[:200]
                if len(val) >= 5:
                    return val
        return None

    def _detect_type_procedure(self, text: str) -> str:
        """Détermine le type de procédure depuis le texte."""
        text_lower = text.lower()
        for type_proc, keywords in self.TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return type_proc
        return "ouvert"  # Défaut

    def _detect_secteur(self, text: str) -> str:
        """Détecte le secteur d'activité de l'AO."""
        text_lower = text.lower()
        scores = {}
        for secteur, keywords in self.SECTEUR_KEYWORDS.items():
            score = sum(text_lower.count(kw) for kw in keywords)
            if score > 0:
                scores[secteur] = score
        if not scores:
            return "autre"
        return max(scores, key=scores.get)

    def _extract_date_cloture(self, text: str) -> Optional[date]:
        """Extrait la date limite de soumission."""
        # Pattern 1 : date après mot-clé
        p1 = (
            r"(?:date\s+limite|cl[oô]ture|d[eé]p[oô]t|soumission|remise\s+des\s+offres)"
            r"\s*:?\s*(?:le\s+|au\s+plus\s+tard\s+le\s+)?"
            r"(\d{1,2})\s+(janvier|f[eé]vrier|mars|avril|mai|juin|juillet|"
            r"ao[uû]t|septembre|octobre|novembre|d[eé]cembre)\s+(\d{4})"
        )
        m = re.search(p1, text, re.IGNORECASE)
        if m:
            return self._parse_french_date(m.group(1), m.group(2), m.group(3))

        # Pattern 2 : date ISO
        m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        if m:
            try:
                return date.fromisoformat(m.group(1))
            except ValueError:
                pass

        # Pattern 3 : format JJ/MM/AAAA
        m3 = re.search(r'(\d{2})/(\d{2})/(\d{4})', text)
        if m3:
            try:
                d = date(int(m3.group(3)), int(m3.group(2)), int(m3.group(1)))
                if d.year >= 2024:
                    return d
            except ValueError:
                pass

        # Pattern 4 : date en français sans mot-clé (chercher toute date future)
        p4 = r'(\d{1,2})\s+(janvier|f[eé]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[eé]cembre)\s+(\d{4})'
        for m in re.finditer(p4, text, re.IGNORECASE):
            d = self._parse_french_date(m.group(1), m.group(2), m.group(3))
            if d and d.year >= 2024:
                return d

        return None

    def _parse_french_date(self, jour: str, mois_str: str, annee: str) -> Optional[date]:
        """Convertit une date en français en objet date."""
        mois_map = {
            "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4,
            "mai": 5, "juin": 6, "juillet": 7, "août": 8, "aout": 8,
            "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
        }
        try:
            return date(int(annee), mois_map[mois_str.lower()], int(jour))
        except (ValueError, KeyError):
            return None

    def _extract_montant(self, text: str) -> Optional[int]:
        """Extrait le montant estimé en FCFA."""
        for pattern in self.MONTANT_PATTERNS:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                val_str = re.sub(r"\s+", "", m.group(1))
                try:
                    val = int(float(val_str.replace(",", ".")))
                    # Sanity : entre 100 000 et 100 milliards FCFA
                    if 100_000 <= val <= 100_000_000_000:
                        return val
                except ValueError:
                    pass
        return None

    def _compute_confidence(self, ao: AORaw) -> float:
        """Calcule un score de confiance pour le parsing (0.0 à 1.0)."""
        score = 0.0
        if ao.titre and len(ao.titre) > 20:   score += 0.3
        if ao.reference:                        score += 0.2
        if ao.autorite_contractante:            score += 0.2
        if ao.date_cloture:                     score += 0.2
        if ao.type_procedure != "ouvert":       score += 0.05
        if ao.secteur != "autre":               score += 0.05
        return round(min(score, 1.0), 2)


class LLMFallbackParser:
    """
    Fallback : utilise l'API Claude pour les AO dont la confiance < 0.5.
    """

    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def parse(self, texte_brut: str) -> Optional[dict]:
        """
        Envoie le texte brut à Claude et demande une extraction JSON structurée.

        Returns:
            Dict avec les champs extraits, ou None si échec.
        """
        import json

        prompt = f"""Tu es un expert en marchés publics du Burkina Faso.
Extrait les informations suivantes depuis ce texte d'appel d'offres.
Réponds UNIQUEMENT avec un JSON valide, sans texte autour.

Champs à extraire :
- titre (string, titre complet du marché)
- reference (string ou null, référence officielle ex: 2026-001/MENA/...)
- autorite_contractante (string, ex: "Ministère de l'Éducation / MENA")
- type_procedure (string: "ouvert"|"restreint"|"dpx"|"ami"|"rfp"|"rfq")
- secteur (string: "informatique"|"btp"|"sante"|"agriculture"|"conseil"|"equipement"|"transport"|"energie"|"education"|"autre")
- date_cloture (string ISO YYYY-MM-DD ou null)
- montant_estime (integer FCFA ou null)

Texte AO :
---
{texte_brut[:3000]}
---"""

        try:
            msg = self.client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=config.CLAUDE_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            # Nettoyer les backticks éventuels
            raw = re.sub(r"^```json\s*|```\s*$", "", raw.strip())
            data = json.loads(raw)
            logger.info("Fallback LLM utilisé avec succès")
            return data
        except Exception as e:
            logger.error(f"Erreur LLM fallback : {e}")
            return None
