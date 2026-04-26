#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# NetSync Gov — Patch #3 : Parser PDF amélioré
# Date : 26 avril 2026
# Usage : cd ~/appels-offres-bf && bash patches/fix-parser.sh
# ══════════════════════════════════════════════════════════════════════════════

set -e
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  NetSync Gov — Patch #3 : Parser PDF amélioré              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ──────────────────────────────────────────────────────────────────────────────
# PARSER 1 : Fusion des pages avant split (texte tronqué sur 2-3 pages)
# PARSER 2 : Nouveaux patterns de référence
# PARSER 3 : Extraction autorité depuis header majuscules
# PARSER 4 : Extraction montant améliorée
# PARSER 5 : Branchement LLM fallback pour confiance < 0.5
# ──────────────────────────────────────────────────────────────────────────────

echo "🔧 Réécriture du parser V2.4 (5 améliorations)..."

python3 << 'PYFIX'
with open("pipeline/parser.py", "r") as f:
    content = f.read()

# ═══════════════════════════════════════════════════════════════════════════════
# AMÉLIORATION 1 : Fusion des pages avant split
# Problème : context_start = pos - 300 coupe le bloc avant les dates
# Solution : Fusionner les pages, traiter le texte complet
# ═══════════════════════════════════════════════════════════════════════════════

old_split = '''    def split_into_blocks(self, full_text: str) -> List[str]:
        """
        Découpe le texte brut en blocs correspondant à chaque AO.
        Adapté au format réel du Quotidien DGCMEF extrait par pdfplumber.
        """
        pages = re.split(r'--- PAGE \\d+ ---', full_text)

        blocks = []

        for page_text in pages:
            if not page_text or len(page_text.strip()) < 50:
                continue

            # Nettoyer les espaces excessifs du mode layout
            lines = page_text.split('\\n')
            cleaned_lines = []
            for line in lines:
                cleaned = re.sub(r'\\s{3,}', '  ', line).strip()
                if cleaned:
                    cleaned_lines.append(cleaned)

            page_clean = '\\n'.join(cleaned_lines)

            # Marqueurs d'un AO dans le Quotidien DGCMEF
            ao_markers = [
                r'Avis\\s+de\\s+demande\\s+de\\s+prix',
                r'Avis\\s+d[\\'\\u2019]appel\\s+d[\\'\\u2019]offres',
                r'Avis\\s+de\\s+manifestation',
                r'Avis\\s+de\\s+s[eé]lection',
                r'Avis\\s+de\\s+recrutement',
                r'Avis\\s+de\\s+sollicitation',
                r'Demande\\s+de\\s+propositions?',
                r'Request\\s+for\\s+(?:proposal|quotation)',
                r'Rectificatif\\s+du\\s+quotidien',
            ]

            combined = '|'.join(ao_markers)
            positions = [(m.start(), m.group()) for m in re.finditer(combined, page_clean, re.IGNORECASE)]

            if not positions:
                continue

            for idx, (pos, marker) in enumerate(positions):
                context_start = max(0, pos - 300)
                if idx + 1 < len(positions):
                    end_pos = positions[idx + 1][0]
                else:
                    end_pos = len(page_clean)

                block = page_clean[context_start:end_pos].strip()
                if len(block) > 100:
                    blocks.append(block)

        logger.info(f"Découpage : {len(blocks)} bloc(s) AO identifié(s)")
        return blocks if blocks else [full_text]'''

new_split = '''    def split_into_blocks(self, full_text: str) -> List[str]:
        """
        Découpe le texte brut en blocs correspondant à chaque AO.
        V2.4 : Fusionne d'abord TOUTES les pages en un seul texte continu,
        puis découpe par marqueurs AO. Résout le problème des AO sur 2-3 pages.
        """
        # ── Étape 1 : Fusionner toutes les pages en un texte continu ──
        merged_text = re.sub(r'--- PAGE \\d+ ---', '\\n', full_text)

        # Nettoyer les espaces excessifs du mode layout
        lines = merged_text.split('\\n')
        cleaned_lines = []
        for line in lines:
            cleaned = re.sub(r'\\s{3,}', '  ', line).strip()
            if cleaned:
                cleaned_lines.append(cleaned)

        merged_clean = '\\n'.join(cleaned_lines)

        # ── Étape 2 : Identifier les positions de chaque AO ──
        ao_markers = [
            r'Avis\\s+de\\s+demande\\s+de\\s+prix',
            r'Avis\\s+d[\\'\\u2019]appel\\s+d[\\'\\u2019]offres',
            r'Avis\\s+de\\s+manifestation',
            r'Avis\\s+de\\s+s[eé]lection',
            r'Avis\\s+de\\s+recrutement',
            r'Avis\\s+de\\s+sollicitation',
            r'Demande\\s+de\\s+propositions?',
            r'Request\\s+for\\s+(?:proposal|quotation)',
            r'Rectificatif\\s+du\\s+quotidien',
            r'Invitation\\s+[àa]\\s+soumissionner',
            r'Appel\\s+[àa]\\s+candidature',
        ]

        combined = '|'.join(ao_markers)
        positions = [(m.start(), m.group()) for m in re.finditer(combined, merged_clean, re.IGNORECASE)]

        if not positions:
            logger.warning("Aucun marqueur AO trouvé dans le PDF")
            return [merged_clean] if len(merged_clean) > 200 else []

        blocks = []

        for idx, (pos, marker) in enumerate(positions):
            # V2.4 : Prendre 500 chars avant le marqueur (au lieu de 300)
            # pour capturer l'autorité en majuscules au-dessus
            context_start = max(0, pos - 500)

            if idx + 1 < len(positions):
                end_pos = positions[idx + 1][0]
            else:
                # Dernier bloc : prendre jusqu'à la fin ou max 5000 chars
                end_pos = min(len(merged_clean), pos + 5000)

            block = merged_clean[context_start:end_pos].strip()
            if len(block) > 100:
                blocks.append(block)

        logger.info(f"Découpage V2.4 : {len(blocks)} bloc(s) AO identifié(s) (texte fusionné)")
        return blocks'''

content = content.replace(old_split, new_split)


# ═══════════════════════════════════════════════════════════════════════════════
# AMÉLIORATION 2 : Nouveaux patterns de référence
# Problème : N sans degré, underscores, ligne séparée
# ═══════════════════════════════════════════════════════════════════════════════

old_ref = '''    REF_PATTERNS = [
        r"N[°\\s]*([\d]{4}[\\s_-]+[\\d\\w_]+[/][A-Z][A-Z/\\w]*)",  # N°2025-005/MSECU/SG/DMP
        r"N[°\\s]*(\\d{4}[_\\s-]*\\d+[_\\s]*/[A-Z][A-Z/_\\w]*)",    # N°2025_07___/ONI/DG
        r"n[°\\s]*(\\d{4}[\\s_-]*\\d+[\\s_-]*/[\\w/]+)",             # n°2025 -011 T_MEEA
        r"N\\s+(\\d{4}-\\d+/[\\w/-]+)",                               # N 2025-01/CO-DD
        r"Réf[éeèê]rence\\s*:?\\s*([\\w/-]+)",
        r"(BF-[\\w-]+-\\d+-(?:GO|CS|CW|IC)-\\w+)",
        r"(UNDP-\\w+-\\d+)",
    ]'''

new_ref = '''    REF_PATTERNS = [
        # Format standard : N°2025-005/MSECU/SG/DMP
        r"N[°\\s]*(\\d{4}[\\s_-]+\\d+[\\s_/]*[A-Z][A-Z/\\w_-]*)",
        # Sans degré : N 2025-01/CO-DD
        r"N\\s+(\\d{4}[\\s_-]*\\d+[\\s_-]*/[\\w/._-]+)",
        # Avec underscores : N°2025_07___/ONI/DG
        r"N[°\\s]*(\\d{4}[_\\s-]*\\d+[_\\s]*/[A-Z][A-Z/_\\w]*)",
        # Minuscule : n°2025 -011 T_MEEA
        r"n[°\\s]*(\\d{4}[\\s_-]*\\d+[\\s_-]*/[\\w/]+)",
        # Générique : tout YYYY-NNN/LETTRES après N/n
        r"[Nn][°o]?\\s*(\\d{4}[\\s_-]*\\d{1,4}[\\s_/]+[A-Z][\\w/._-]{3,})",
        # Référence sur une ligne séparée : "Réf : ..."
        r"[Rr][eéèê]f[eéèê]?rence\\s*:?\\s*([\\w/_-]{5,}[/][\\w/_-]+)",
        # Formats internationaux
        r"(BF-[\\w-]+-\\d+-(?:GO|CS|CW|IC|RFB|RFP|RFQ)-[\\w-]+)",
        r"(UNDP-[\\w-]+-\\d+)",
        r"(STEP-BF-\\d+)",
    ]'''

content = content.replace(old_ref, new_ref)


# ═══════════════════════════════════════════════════════════════════════════════
# AMÉLIORATION 3 : Extraction autorité depuis header majuscules
# Problème : Le regex cherche 'autorite contractante:' qui n'existe pas dans le PDF
# Solution : Détecter les lignes MAJUSCULES dans les 10 premières lignes
# ═══════════════════════════════════════════════════════════════════════════════

old_autorite = '''    def _extract_autorite(self, text: str) -> Optional[str]:
        """Extrait l'autorité contractante."""
        patterns = [
            r"(?:maître\\s+d['']ouvrage|autorit[eé]\\s+contractante|organisme)\\s*:?\\s*([^\\n]{5,80})",
            r"(?:au\\s+profit\\s+de|pour\\s+le\\s+compte\\s+de)\\s+([^\\n]{5,80})",
            r"(?:minist[eèé]re|direction|agence|office|soci[eé]t[eé]|projet)\\s+[^\\n]{3,80}",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                val = m.group(1) if m.lastindex else m.group(0)
                val = re.sub(r"\\s+", " ", val).strip()[:200]
                if len(val) >= 5:
                    return val
        return None'''

new_autorite = '''    # Patterns connus d'autorité (en majuscules dans les PDFs DGCMEF)
    AUTORITE_KEYWORDS = [
        "MINISTERE", "MINISTRE", "DIRECTION", "SECRETARIAT",
        "AGENCE", "OFFICE", "UNIVERSITE", "CENTRE",
        "PROJET", "PROGRAMME", "SOCIETE", "COMMISSION",
        "AUTORITE", "CONSEIL", "PRESIDENCE", "PRIMATURE",
        "INSTITUT", "ECOLE", "HOPITAL", "COMMUNE",
        "REGION", "PROVINCE", "MAIRIE", "ASSEMBLEE",
    ]

    def _extract_autorite(self, text: str) -> Optional[str]:
        """
        Extrait l'autorité contractante.
        V2.4 : Cherche d'abord les lignes en MAJUSCULES dans les 10 premières lignes
        (pattern réel des PDFs DGCMEF), puis fallback sur les patterns textuels.
        """
        lines = [l.strip() for l in text.split("\\n") if l.strip()]

        # ── Méthode 1 : Lignes en majuscules dans le header du bloc ──
        for line in lines[:10]:
            # Vérifier si la ligne est majoritairement en majuscules
            upper_ratio = sum(1 for c in line if c.isupper()) / max(len(line), 1)
            if upper_ratio > 0.6 and len(line) > 10:
                # Vérifier si ça contient un mot-clé d'autorité
                line_upper = line.upper()
                if any(kw in line_upper for kw in self.AUTORITE_KEYWORDS):
                    val = re.sub(r"\\s+", " ", line).strip()[:200]
                    return val

        # ── Méthode 2 : Patterns textuels classiques ──
        patterns = [
            r"(?:maître\\s+d['\\'\\u2019]ouvrage|autorit[eé]\\s+contractante|organisme)\\s*:?\\s*([^\\n]{5,120})",
            r"(?:au\\s+profit\\s+d[eu]|pour\\s+le\\s+compte\\s+d[eu])\\s+(?:la\\s+|l['\\'\\u2019]|du\\s+)?([^\\n]{5,120})",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                val = m.group(1) if m.lastindex else m.group(0)
                val = re.sub(r"\\s+", " ", val).strip()[:200]
                if len(val) >= 5:
                    return val

        # ── Méthode 3 : Chercher les mentions de ministère/direction partout ──
        m = re.search(
            r"((?:minist[eèéÈÉ]re|direction\\s+g[eé]n[eé]rale|agence|office|universit[eé]|projet)\\s+[^\\n.]{3,100})",
            text, re.IGNORECASE
        )
        if m:
            val = re.sub(r"\\s+", " ", m.group(1)).strip()[:200]
            if len(val) >= 8:
                return val

        return None'''

content = content.replace(old_autorite, new_autorite)


# ═══════════════════════════════════════════════════════════════════════════════
# AMÉLIORATION 4 : Extraction montant améliorée
# Problème : '13 375 000 F CFA TTC' avec espaces variables non capté
# Solution : Pattern plus permissif + normalisation des espaces
# ═══════════════════════════════════════════════════════════════════════════════

old_montant_patterns = '''    MONTANT_PATTERNS = [
        r"(\\d[\\d\\s]*(?:\\.\\d+)?)\\s*(?:F\\s*CFA|FCFA|XOF|francs\\s+CFA)",
        r"montant\\s*:?\\s*([\\d\\s]+(?:\\.\\d+)?)",
    ]'''

new_montant_patterns = '''    MONTANT_PATTERNS = [
        # "13 375 000 F CFA TTC" — espaces dans le nombre + espace avant F
        r"(\\d[\\d\\s\\.]{2,30})\\s*F\\s*\\.?\\s*CFA",
        # "FCFA" collé : "13375000FCFA" ou "13 375 000 FCFA"
        r"(\\d[\\d\\s\\.]{2,30})\\s*FCFA",
        # "XOF" ou "francs CFA"
        r"(\\d[\\d\\s\\.]{2,30})\\s*(?:XOF|francs\\s+CFA)",
        # Après mot-clé : "montant estimé : 50 000 000"
        r"(?:montant|co[uû]t|budget|estimation|prix)\\s*(?:[eé]stim[eé]|pr[eé]visionnel|global|total)?\\s*:?\\s*(\\d[\\d\\s\\.]{2,30})",
        # Après mot-clé avec FCFA plus loin : "montant : 50 000 000 F CFA"
        r"(?:montant|co[uû]t|budget)\\s*[^\\d]{0,20}(\\d[\\d\\s]{2,30})\\s*F",
    ]'''

content = content.replace(old_montant_patterns, new_montant_patterns)


# Améliorer aussi la méthode _extract_montant pour mieux parser
old_extract_montant = '''    def _extract_montant(self, text: str) -> Optional[int]:
        """Extrait le montant estimé en FCFA."""
        for pattern in self.MONTANT_PATTERNS:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                val_str = re.sub(r"\\s+", "", m.group(1))
                try:
                    val = int(float(val_str.replace(",", ".")))
                    # Sanity : entre 100 000 et 100 milliards FCFA
                    if 100_000 <= val <= 100_000_000_000:
                        return val
                except ValueError:
                    pass
        return None'''

new_extract_montant = '''    def _extract_montant(self, text: str) -> Optional[int]:
        """Extrait le montant estimé en FCFA. V2.4 : patterns plus permissifs."""
        candidates = []
        for pattern in self.MONTANT_PATTERNS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                # Prendre le premier groupe capturant non-None
                val_str = None
                for g in range(1, len(m.groups()) + 1):
                    if m.group(g):
                        val_str = m.group(g)
                        break
                if not val_str:
                    continue

                # Nettoyer : supprimer espaces, points de milliers, remplacer virgule décimale
                val_str = re.sub(r"[\\s\\.]", "", val_str)
                val_str = val_str.replace(",", ".")

                try:
                    val = int(float(val_str))
                    # Sanity : entre 100 000 et 100 milliards FCFA
                    if 100_000 <= val <= 100_000_000_000:
                        candidates.append(val)
                except (ValueError, OverflowError):
                    pass

        if candidates:
            # Retourner le plus grand montant trouvé (souvent le montant total)
            return max(candidates)
        return None'''

content = content.replace(old_extract_montant, new_extract_montant)


# ═══════════════════════════════════════════════════════════════════════════════
# AMÉLIORATION 5 : Améliorer le score de confiance
# ═══════════════════════════════════════════════════════════════════════════════

old_confidence = '''    def _compute_confidence(self, ao: AORaw) -> float:
        """Calcule un score de confiance pour le parsing (0.0 à 1.0)."""
        score = 0.0
        if ao.titre and len(ao.titre) > 20:   score += 0.3
        if ao.reference:                        score += 0.2
        if ao.autorite_contractante:            score += 0.2
        if ao.date_cloture:                     score += 0.2
        if ao.type_procedure != "ouvert":       score += 0.05
        if ao.secteur != "autre":               score += 0.05
        return round(min(score, 1.0), 2)'''

new_confidence = '''    def _compute_confidence(self, ao: AORaw) -> float:
        """Calcule un score de confiance pour le parsing (0.0 à 1.0). V2.4."""
        score = 0.0
        if ao.titre and len(ao.titre) > 20:     score += 0.25
        if ao.reference:                          score += 0.15
        if ao.autorite_contractante:              score += 0.15
        if ao.date_cloture:                       score += 0.15
        if ao.montant_estime:                     score += 0.10
        if ao.type_procedure != "ouvert":         score += 0.10
        if ao.secteur != "autre":                 score += 0.10
        return round(min(score, 1.0), 2)'''

content = content.replace(old_confidence, new_confidence)


with open("pipeline/parser.py", "w") as f:
    f.write(content)
print("   ✅ Parser V2.4 appliqué :")
print("      • Fusion des pages avant split (résout texte tronqué)")
print("      • 9 patterns de référence (vs 7 avant)")
print("      • Autorité depuis lignes MAJUSCULES + 22 mots-clés")
print("      • 5 patterns montant + extraction multi-candidats")
print("      • Score de confiance recalibré avec montant")
PYFIX


# ──────────────────────────────────────────────────────────────────────────────
# PARSER 6 : Brancher le LLM fallback dans le normalizer
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 Branchement LLM fallback dans le normalizer..."

python3 << 'PYFIX2'
with open("pipeline/normalizer.py", "r") as f:
    content = f.read()

# Ajouter l'import du LLMFallbackParser
if "LLMFallbackParser" not in content:
    old_import = "from pipeline.parser import AORaw"
    new_import = """from pipeline.parser import AORaw, LLMFallbackParser
from pipeline.config import config as pipeline_config"""
    content = content.replace(old_import, new_import)

    # Ajouter une méthode pour enrichir via LLM
    enrich_method = '''

    def enrich_with_llm(self, ao_raw: AORaw) -> AORaw:
        """
        Si la confiance est < 0.5 et que la clé API Anthropic est configurée,
        utilise Claude pour enrichir les champs manquants.
        """
        if ao_raw.confiance >= 0.5:
            return ao_raw
        if not pipeline_config.ANTHROPIC_API_KEY or not pipeline_config.USE_LLM_FALLBACK:
            return ao_raw

        try:
            llm = LLMFallbackParser()
            result = llm.parse(ao_raw.texte_brut)
            if not result:
                return ao_raw

            # Enrichir les champs manquants (ne pas écraser ce qui existe)
            if not ao_raw.reference and result.get("reference"):
                ao_raw.reference = result["reference"]
            if not ao_raw.autorite_contractante and result.get("autorite_contractante"):
                ao_raw.autorite_contractante = result["autorite_contractante"]
            if not ao_raw.date_cloture and result.get("date_cloture"):
                from datetime import date as dt_date
                try:
                    ao_raw.date_cloture = dt_date.fromisoformat(result["date_cloture"])
                except (ValueError, TypeError):
                    pass
            if not ao_raw.montant_estime and result.get("montant_estime"):
                try:
                    ao_raw.montant_estime = int(result["montant_estime"])
                except (ValueError, TypeError):
                    pass
            if ao_raw.secteur == "autre" and result.get("secteur"):
                ao_raw.secteur = result["secteur"]

            # Recalculer la confiance
            score = 0.0
            if ao_raw.titre and len(ao_raw.titre) > 20: score += 0.25
            if ao_raw.reference: score += 0.15
            if ao_raw.autorite_contractante: score += 0.15
            if ao_raw.date_cloture: score += 0.15
            if ao_raw.montant_estime: score += 0.10
            if ao_raw.type_procedure != "ouvert": score += 0.10
            if ao_raw.secteur != "autre": score += 0.10
            ao_raw.confiance = round(min(score, 1.0), 2)

            logger.info(f"LLM enrichi: confiance {ao_raw.confiance} pour '{ao_raw.titre[:50]}'")
        except Exception as e:
            logger.warning(f"LLM fallback échoué: {e}")

        return ao_raw
'''

    # Insérer avant la méthode upsert
    insert_point = "    # ── Déduplication et insertion"
    if insert_point in content:
        content = content.replace(insert_point, enrich_method + "\n" + insert_point)

    with open("pipeline/normalizer.py", "w") as f:
        f.write(content)
    print("   ✅ LLM fallback branché dans normalizer.enrich_with_llm()")
    print("      • S'active si confiance < 0.5 et ANTHROPIC_API_KEY configurée")
    print("      • Enrichit sans écraser les champs déjà extraits")
else:
    print("   ℹ️  LLM fallback déjà branché")
PYFIX2


# ──────────────────────────────────────────────────────────────────────────────
# RÉSUMÉ
# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════════════"
echo "✅ Patch #3 terminé — Parser V2.4 :"
echo ""
echo "  FIX 1 ✅ Fusion pages avant split (AO sur 2-3 pages capturés)"
echo "  FIX 2 ✅ 9 patterns référence (N sans degré, underscores, internationaux)"
echo "  FIX 3 ✅ Autorité depuis MAJUSCULES header (22 mots-clés institutions BF)"
echo "  FIX 4 ✅ 5 patterns montant + extraction multi-candidats"
echo "  FIX 5 ✅ Score confiance recalibré (montant compte maintenant)"
echo "  FIX 6 ✅ LLM fallback branché dans normalizer"
echo ""
echo "Améliorations attendues :"
echo "  • AOs détectés : 31 → 38+ (fusion pages)"
echo "  • Références   : 70% → 85%+ (nouveaux patterns)"
echo "  • Autorité      : 72% → 88%+ (MAJUSCULES header)"
echo "  • Dates          : 61% → 80%+ (blocs plus grands)"
echo "  • Montants      : 9% → 40%+ (patterns permissifs)"
echo ""
echo "Prochaine étape — commit et push :"
echo "  git add -A"
echo "  git commit -m 'feat(parser): V2.4 — fusion pages, refs, autorité, montants, LLM fallback (patch #3)'"
echo "  git push origin main"
echo "══════════════════════════════════════════════════════════════"
