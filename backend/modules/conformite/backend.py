"""
NetSync Gov Conformité — Backend FastAPI
Gestion du coffre-fort administratif : pièces, alertes, score de conformité.
NB : La table pieces_administratives est déjà créée dans le module Candidature.
     Ce module l'étend avec des endpoints dédiés et la logique de conformité.
"""
import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from backend.database import get_db
from backend.security import require_pro
from backend.models import Abonne

logger = logging.getLogger("netsync.conformite")

router = APIRouter(prefix="/api/v1/conformite", tags=["Conformité"])

# ── Catalogue des pièces avec métadonnées complètes ──────────────────────────

CATALOGUE_PIECES = {
    "asf": {
        "label":        "Attestation de Situation Fiscale (ASF)",
        "sigle":        "ASF",
        "organisme":    "Direction Générale des Impôts (DGI)",
        "validite_j":   90,
        "obligatoire":  ["ouvert", "restreint", "dpx"],
        "instructions": (
            "Obtenir via SECOP : https://secop.finances.bf\n"
            "1. Se connecter avec les identifiants IFU\n"
            "2. Aller dans 'Mes attestations' → 'Demander ASF'\n"
            "3. Télécharger le PDF généré automatiquement\n"
            "Délai : immédiat si situation fiscale à jour."
        ),
        "lien_renouvellement": "https://secop.finances.bf",
        "urgence_couleur": "rouge",
    },
    "cnss": {
        "label":        "Attestation de Situation Cotisante CNSS",
        "sigle":        "CNSS",
        "organisme":    "Caisse Nationale de Sécurité Sociale",
        "validite_j":   90,
        "obligatoire":  ["ouvert", "restreint", "dpx"],
        "instructions": (
            "Obtenir via SECOP ou directement à la CNSS :\n"
            "1. Via SECOP : https://secop.finances.bf → 'Attestation CNSS'\n"
            "2. En personne : CNSS Ouagadougou, Avenue de la Nation\n"
            "Conditions : être à jour des cotisations employeur."
        ),
        "lien_renouvellement": "https://secop.finances.bf",
        "urgence_couleur": "rouge",
    },
    "aje": {
        "label":        "Attestation de Jouissance d'Existence (AJE)",
        "sigle":        "AJE",
        "organisme":    "Tribunal de Commerce de Ouagadougou",
        "validite_j":   365,
        "obligatoire":  ["ouvert", "restreint"],
        "instructions": (
            "Obtenir au Tribunal de Commerce :\n"
            "Adresse : Av. de l'Indépendance, Ouagadougou\n"
            "Horaires : Lun-Ven 8h-12h / 15h-17h\n"
            "Documents : Extrait RCCM récent + formulaire de demande\n"
            "Délai : 24 à 72h\nCoût : ~5 000 FCFA"
        ),
        "lien_renouvellement": None,
        "urgence_couleur": "orange",
    },
    "rccm": {
        "label":        "Registre du Commerce et du Crédit Mobilier (RCCM)",
        "sigle":        "RCCM",
        "organisme":    "CEFORE / Tribunal de Commerce",
        "validite_j":   None,  # Pas d'expiration automatique
        "obligatoire":  ["ouvert", "restreint", "rfp"],
        "instructions": (
            "Obtenir au CEFORE (Centre de Facilitation des Entreprises) :\n"
            "Adresse : Ouagadougou\n"
            "À mettre à jour uniquement en cas de changement de statut ou de dirigeant."
        ),
        "lien_renouvellement": None,
        "urgence_couleur": "bleu",
    },
    "ifu": {
        "label":        "Identifiant Fiscal Unique (IFU)",
        "sigle":        "IFU",
        "organisme":    "Direction Générale des Impôts (DGI)",
        "validite_j":   None,
        "obligatoire":  ["ouvert", "restreint", "dpx", "rfp"],
        "instructions": "Délivré à la création de l'entreprise. Permanent.",
        "lien_renouvellement": None,
        "urgence_couleur": "bleu",
    },
    "statuts": {
        "label":        "Statuts de la société",
        "sigle":        "Statuts",
        "organisme":    "Notaire / CEFORE",
        "validite_j":   None,
        "obligatoire":  ["ouvert", "restreint", "rfp"],
        "instructions": "Mettre à jour uniquement en cas de modification (capital, associés, siège).",
        "lien_renouvellement": None,
        "urgence_couleur": "bleu",
    },
    "attestation_bancaire": {
        "label":        "Attestation bancaire de solvabilité",
        "sigle":        "Attestation bancaire",
        "organisme":    "Banque de l'entreprise",
        "validite_j":   30,
        "obligatoire":  [],  # Parfois requise, pas systématique
        "instructions": (
            "Demander à votre banque une lettre de solvabilité ou une attestation de domiciliation.\n"
            "Délai : 24 à 72h selon la banque.\n"
            "Coût : variable (0 à 50 000 FCFA)."
        ),
        "lien_renouvellement": None,
        "urgence_couleur": "rouge",
    },
    "casier_judiciaire": {
        "label":        "Casier judiciaire du dirigeant",
        "sigle":        "Casier judiciaire",
        "organisme":    "Tribunal de Grande Instance",
        "validite_j":   90,
        "obligatoire":  [],
        "instructions": (
            "Obtenir au Tribunal de Grande Instance de Ouagadougou.\n"
            "Documents : CNI ou passeport du dirigeant\n"
            "Délai : immédiat à 48h\nCoût : ~1 000 FCFA"
        ),
        "lien_renouvellement": None,
        "urgence_couleur": "orange",
    },
    "cv": {
        "label":        "CV du consultant / expert clé",
        "sigle":        "CV",
        "organisme":    "Interne",
        "validite_j":   None,
        "obligatoire":  ["ami", "rfp"],
        "instructions": "À mettre à jour régulièrement avec les nouvelles missions et formations.",
        "lien_renouvellement": None,
        "urgence_couleur": "bleu",
    },
    "reference_marche": {
        "label":        "Lettre de référence de marché similaire",
        "sigle":        "Référence",
        "organisme":    "Autorité contractante précédente",
        "validite_j":   None,
        "obligatoire":  ["ouvert", "restreint", "ami", "rfp"],
        "instructions": (
            "Demander à chaque client (autorité contractante) une attestation de bonne exécution.\n"
            "Inclure : titre du marché, montant, date, appréciation de la qualité."
        ),
        "lien_renouvellement": None,
        "urgence_couleur": "bleu",
    },
}


def get_statut_piece(date_expiration: Optional[date], validite_j: Optional[int]) -> dict:
    """
    Calcule le statut d'une pièce administrative.
    Returns: dict avec statut, jours_restants, couleur, message
    """
    if date_expiration is None:
        return {
            "statut":         "permanent",
            "jours_restants": None,
            "couleur":        "bleu",
            "message":        "Pièce permanente — vérifier en cas de changement de statut",
        }

    today = date.today()
    delta = (date_expiration - today).days

    if delta < 0:
        return {
            "statut":         "expiree",
            "jours_restants": delta,
            "couleur":        "rouge",
            "message":        f"Expirée depuis {abs(delta)} jour(s) — à renouveler immédiatement",
        }
    if delta <= 7:
        return {
            "statut":         "critique",
            "jours_restants": delta,
            "couleur":        "rouge",
            "message":        f"Expire dans {delta} jour(s) — renouvellement URGENT",
        }
    if delta <= 15:
        return {
            "statut":         "urgent",
            "jours_restants": delta,
            "couleur":        "orange",
            "message":        f"Expire dans {delta} jour(s) — renouvellement recommandé",
        }
    if delta <= 30:
        return {
            "statut":         "attention",
            "jours_restants": delta,
            "couleur":        "jaune",
            "message":        f"Expire dans {delta} jour(s) — prévoir le renouvellement",
        }

    return {
        "statut":         "valide",
        "jours_restants": delta,
        "couleur":        "vert",
        "message":        f"Valide encore {delta} jour(s)",
    }


def calculer_score_conformite(abonne_id: str, db: Session) -> dict:
    """
    Calcule le score de conformité global de l'entreprise.
    Basé sur les 5 pièces clés obligatoires pour un AO ouvert.
    """
    PIECES_CLES = ["asf", "cnss", "aje", "rccm", "ifu"]

    pieces = db.execute(
        text("""
            SELECT type_piece, date_expiration, est_valide
            FROM pieces_administratives
            WHERE abonne_id = :id
              AND type_piece = ANY(:types)
            ORDER BY updated_at DESC
        """),
        {"id": abonne_id, "types": PIECES_CLES}
    ).fetchall()

    types_presents = {p.type_piece for p in pieces}
    types_valides  = {p.type_piece for p in pieces if p.est_valide}

    manquantes = [t for t in PIECES_CLES if t not in types_presents]
    expirees   = [t for t in types_presents if t not in types_valides]

    score = int(len(types_valides) / len(PIECES_CLES) * 100)

    if score == 100:
        niveau = "conforme"
        message = "Votre dossier administratif est complet et valide."
    elif score >= 80:
        niveau = "quasi_conforme"
        message = "Quelques pièces à renouveler avant la prochaine candidature."
    elif score >= 60:
        niveau = "attention"
        message = "Plusieurs pièces manquantes ou expirées."
    else:
        niveau = "non_conforme"
        message = "Dossier administratif incomplet — candidature risquée."

    return {
        "score":         score,
        "niveau":        niveau,
        "message":       message,
        "pieces_valides": list(types_valides),
        "manquantes":    [
            {"type": t, **CATALOGUE_PIECES.get(t, {})} for t in manquantes
        ],
        "expirees":      [
            {"type": t, **CATALOGUE_PIECES.get(t, {})} for t in expirees
        ],
    }


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/score")
def score_conformite(
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """Score global de conformité administrative de l'entreprise."""
    return calculer_score_conformite(str(abonne.id), db)


@router.get("/pieces")
def mes_pieces(
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """
    Liste complète des pièces avec statut temps réel.
    Enrichit les données BDD avec le catalogue et le calcul de statut.
    """
    pieces_bdd = db.execute(
        text("""
            SELECT id, type_piece, nom_fichier, url_stockage,
                   date_emission, date_expiration, est_valide, notes, updated_at
            FROM pieces_administratives
            WHERE abonne_id = :id
            ORDER BY
                CASE
                    WHEN date_expiration IS NULL THEN 2
                    WHEN date_expiration < CURRENT_DATE THEN 0
                    ELSE 1
                END,
                date_expiration ASC
        """),
        {"id": str(abonne.id)}
    ).fetchall()

    # Pièces présentes en BDD
    types_presents = {p.type_piece for p in pieces_bdd}

    result = []
    # Pièces enregistrées
    for p in pieces_bdd:
        catalogue = CATALOGUE_PIECES.get(p.type_piece, {})
        statut_info = get_statut_piece(p.date_expiration, catalogue.get("validite_j"))
        result.append({
            "id":              str(p.id),
            "type_piece":      p.type_piece,
            "label":           catalogue.get("label", p.type_piece),
            "organisme":       catalogue.get("organisme"),
            "nom_fichier":     p.nom_fichier,
            "url_stockage":    p.url_stockage,
            "date_emission":   p.date_emission.isoformat() if p.date_emission else None,
            "date_expiration": p.date_expiration.isoformat() if p.date_expiration else None,
            "notes":           p.notes,
            "statut":          statut_info,
            "instructions":    catalogue.get("instructions"),
            "lien_renouvellement": catalogue.get("lien_renouvellement"),
            "enregistree":     True,
        })

    # Pièces du catalogue manquantes (non encore enregistrées)
    for type_piece, info in CATALOGUE_PIECES.items():
        if type_piece not in types_presents:
            result.append({
                "id":              None,
                "type_piece":      type_piece,
                "label":           info["label"],
                "organisme":       info["organisme"],
                "nom_fichier":     None,
                "url_stockage":    None,
                "date_emission":   None,
                "date_expiration": None,
                "notes":           None,
                "statut": {
                    "statut":         "manquante",
                    "jours_restants": None,
                    "couleur":        "gris",
                    "message":        "Pièce non encore enregistrée",
                },
                "instructions":    info.get("instructions"),
                "lien_renouvellement": info.get("lien_renouvellement"),
                "enregistree":     False,
            })

    return result


@router.get("/calendrier")
def calendrier_echeances(
    jours: int = 90,
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """
    Calendrier des échéances sur les N prochains jours.
    Trié chronologiquement pour faciliter la planification.
    """
    limite = date.today() + timedelta(days=jours)
    pieces = db.execute(
        text("""
            SELECT type_piece, date_expiration, nom_fichier
            FROM pieces_administratives
            WHERE abonne_id = :id
              AND date_expiration IS NOT NULL
              AND date_expiration <= :limite
            ORDER BY date_expiration ASC
        """),
        {"id": str(abonne.id), "limite": limite}
    ).fetchall()

    echeances = []
    for p in pieces:
        catalogue = CATALOGUE_PIECES.get(p.type_piece, {})
        statut = get_statut_piece(p.date_expiration, catalogue.get("validite_j"))
        echeances.append({
            "type_piece":      p.type_piece,
            "label":           catalogue.get("label", p.type_piece),
            "date_expiration": p.date_expiration.isoformat(),
            "jours_restants":  statut["jours_restants"],
            "statut":          statut["statut"],
            "couleur":         statut["couleur"],
            "lien_renouvellement": catalogue.get("lien_renouvellement"),
        })

    return {"jours": jours, "echeances": echeances, "total": len(echeances)}


@router.get("/catalogue")
def catalogue_pieces(abonne: Abonne = Depends(require_pro)):
    """
    Liste de toutes les pièces connues avec leurs métadonnées.
    Utilisé pour afficher la liste complète et les instructions.
    """
    return [
        {
            "type_piece":      k,
            "label":           v["label"],
            "sigle":           v["sigle"],
            "organisme":       v["organisme"],
            "validite_j":      v["validite_j"],
            "obligatoire_pour": v["obligatoire"],
            "instructions":    v["instructions"],
            "lien_renouvellement": v.get("lien_renouvellement"),
        }
        for k, v in CATALOGUE_PIECES.items()
    ]


@router.get("/verifier-candidature/{ao_id}")
def verifier_conformite_pour_ao(
    ao_id: str,
    abonne: Abonne = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """
    Vérifie si l'entreprise a toutes les pièces valides pour candidater à un AO.
    Retourne la liste des blocages et des pièces à renouveler.
    """
    # Récupérer le type de procédure de l'AO
    ao = db.execute(
        text("SELECT type_procedure, titre FROM appels_offres WHERE id = :id"),
        {"id": ao_id}
    ).fetchone()
    if not ao:
        raise HTTPException(status_code=404, detail="AO introuvable")

    type_proc = ao.type_procedure or "ouvert"

    # Pièces obligatoires pour ce type
    obligatoires = [
        k for k, v in CATALOGUE_PIECES.items()
        if type_proc in v["obligatoire"]
    ]

    # Pièces valides de l'abonné
    valides = db.execute(
        text("""
            SELECT type_piece FROM pieces_administratives
            WHERE abonne_id = :abonne_id AND est_valide = true
        """),
        {"abonne_id": str(abonne.id)}
    ).fetchall()
    types_valides = {p.type_piece for p in valides}

    blocages = []
    avertissements = []

    for type_piece in obligatoires:
        info = CATALOGUE_PIECES.get(type_piece, {})
        if type_piece not in types_valides:
            # Vérifier si présente mais expirée
            expiree = db.execute(
                text("""
                    SELECT date_expiration FROM pieces_administratives
                    WHERE abonne_id = :aid AND type_piece = :tp
                    ORDER BY updated_at DESC LIMIT 1
                """),
                {"aid": str(abonne.id), "tp": type_piece}
            ).fetchone()

            if expiree:
                blocages.append({
                    "type_piece": type_piece,
                    "label":      info.get("label", type_piece),
                    "raison":     "expirée",
                    "action":     "Renouveler immédiatement",
                    "lien":       info.get("lien_renouvellement"),
                })
            else:
                blocages.append({
                    "type_piece": type_piece,
                    "label":      info.get("label", type_piece),
                    "raison":     "manquante",
                    "action":     "Obtenir et enregistrer",
                    "lien":       info.get("lien_renouvellement"),
                })
        else:
            # Valide mais expire bientôt ?
            piece = db.execute(
                text("""
                    SELECT date_expiration FROM pieces_administratives
                    WHERE abonne_id = :aid AND type_piece = :tp AND est_valide = true
                    ORDER BY updated_at DESC LIMIT 1
                """),
                {"aid": str(abonne.id), "tp": type_piece}
            ).fetchone()
            if piece and piece.date_expiration:
                jours = (piece.date_expiration - date.today()).days
                if jours <= 15:
                    avertissements.append({
                        "type_piece":      type_piece,
                        "label":           info.get("label", type_piece),
                        "jours_restants":  jours,
                        "date_expiration": piece.date_expiration.isoformat(),
                        "message":         f"Expire dans {jours} j — vérifier avant le dépôt",
                    })

    return {
        "ao_id":          ao_id,
        "ao_titre":       ao.titre,
        "type_procedure": type_proc,
        "peut_candidater": len(blocages) == 0,
        "blocages":        blocages,
        "avertissements":  avertissements,
        "pieces_ok":       len(obligatoires) - len(blocages),
        "pieces_total":    len(obligatoires),
    }
