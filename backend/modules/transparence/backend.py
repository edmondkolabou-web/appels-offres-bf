"""
NetSync Gov Transparence — Backend FastAPI
Portail public d'accès aux données de la commande publique BF.
Tous les endpoints sont publics (pas d'authentification requise).
Rate-limiting géré par Nginx : 30 req/min.
"""
import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from database import get_db

logger = logging.getLogger("netsync.transparence")

router = APIRouter(prefix="/api/v1/transparence", tags=["Transparence"])

# Headers CORS ouverts pour les intégrateurs tiers
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "X-Data-Source": "NetSync Gov — gov.netsync.bf",
    "X-License": "Open Data — Usage libre avec attribution",
}


def open_response(data: dict) -> JSONResponse:
    """Retourne une réponse JSON avec les headers Open Data."""
    return JSONResponse(content=data, headers=CORS_HEADERS)


# ── Portail public AOs ────────────────────────────────────────────────────────

@router.get("/aos")
def search_aos_public(
    q: Optional[str] = Query(None, description="Recherche full-text"),
    secteur: Optional[str] = None,
    autorite: Optional[str] = None,
    statut: Optional[str] = Query("ouvert", description="ouvert|cloture|tous"),
    source: Optional[str] = None,
    date_debut: Optional[date] = None,
    date_fin: Optional[date] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Recherche publique dans tous les appels d'offres indexés.
    Accessible sans authentification. Rate-limited à 30 req/min via Nginx.
    """
    conditions = ["1=1"]
    params: dict = {"offset": (page - 1) * per_page, "limit": per_page}

    if q:
        conditions.append("search_vector @@ plainto_tsquery('french', :q)")
        params["q"] = q
    if secteur:
        conditions.append("secteur = :secteur")
        params["secteur"] = secteur
    if autorite:
        conditions.append("autorite_contractante ILIKE :autorite")
        params["autorite"] = f"%{autorite}%"
    if statut and statut != "tous":
        conditions.append("statut = :statut")
        params["statut"] = statut
    if source:
        conditions.append("source = :source")
        params["source"] = source
    if date_debut:
        conditions.append("date_publication >= :date_debut")
        params["date_debut"] = date_debut
    if date_fin:
        conditions.append("date_publication <= :date_fin")
        params["date_fin"] = date_fin

    where = " AND ".join(conditions)

    total = db.execute(
        text(f"SELECT COUNT(*) FROM appels_offres WHERE {where}"),
        params
    ).scalar()

    rows = db.execute(text(f"""
        SELECT
            id, reference, titre, autorite_contractante, secteur,
            type_procedure, statut, source, date_publication, date_cloture,
            montant_estime, est_urgent, jours_restants, pdf_url
        FROM appels_offres
        WHERE {where}
        ORDER BY date_publication DESC
        LIMIT :limit OFFSET :offset
    """), params).fetchall()

    return open_response({
        "total":     total,
        "page":      page,
        "per_page":  per_page,
        "pages":     (total + per_page - 1) // per_page,
        "source":    "NetSync Gov — Données DGCMEF Burkina Faso",
        "items":     [
            {
                "id":                  str(r.id),
                "reference":           r.reference,
                "titre":               r.titre,
                "autorite":            r.autorite_contractante,
                "secteur":             r.secteur,
                "type_procedure":      r.type_procedure,
                "statut":              r.statut,
                "source":              r.source,
                "date_publication":    r.date_publication.isoformat() if r.date_publication else None,
                "date_cloture":        r.date_cloture.isoformat() if r.date_cloture else None,
                "montant_estime":      r.montant_estime,
                "est_urgent":          r.est_urgent,
                "pdf_url":             r.pdf_url,
                "url_fiche":           f"https://gov.netsync.bf/aos/{r.id}",
            }
            for r in rows
        ],
    })


@router.get("/aos/{ao_id}")
def get_ao_public(ao_id: str, db: Session = Depends(get_db)):
    """Fiche publique complète d'un appel d'offres."""
    ao = db.execute(
        text("SELECT * FROM appels_offres WHERE id = :id"),
        {"id": ao_id}
    ).fetchone()
    if not ao:
        raise HTTPException(status_code=404, detail="AO introuvable")

    # Chercher l'attribution si elle existe
    attribution = db.execute(
        text("SELECT * FROM attributions WHERE ao_id = :id ORDER BY created_at DESC LIMIT 1"),
        {"id": ao_id}
    ).fetchone()

    data = dict(ao._mapping)
    data["id"] = str(data["id"])
    if data.get("date_publication"):
        data["date_publication"] = data["date_publication"].isoformat()
    if data.get("date_cloture"):
        data["date_cloture"] = data["date_cloture"].isoformat()

    if attribution:
        data["attribution"] = {
            "attributaire":     attribution.attributaire,
            "montant_final":    attribution.montant_final,
            "date_signature":   attribution.date_signature.isoformat() if attribution.date_signature else None,
            "source_quotidien": attribution.source_quotidien,
        }

    return open_response({"ao": data, "source": "NetSync Gov — DGCMEF Burkina Faso"})


# ── Tableau des attributions ──────────────────────────────────────────────────

@router.get("/attributions")
def liste_attributions(
    q: Optional[str] = None,
    secteur: Optional[str] = None,
    autorite: Optional[str] = None,
    attributaire: Optional[str] = None,
    annee: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Liste publique des marchés attribués.
    Données extraites du Quotidien DGCMEF (section résultats d'attribution).
    """
    conditions = ["1=1"]
    params: dict = {"offset": (page - 1) * per_page, "limit": per_page}

    if q:
        conditions.append("(a.attributaire ILIKE :q OR ao.titre ILIKE :q)")
        params["q"] = f"%{q}%"
    if secteur:
        conditions.append("ao.secteur = :secteur")
        params["secteur"] = secteur
    if autorite:
        conditions.append("ao.autorite_contractante ILIKE :autorite")
        params["autorite"] = f"%{autorite}%"
    if attributaire:
        conditions.append("a.attributaire ILIKE :attributaire")
        params["attributaire"] = f"%{attributaire}%"
    if annee:
        conditions.append("EXTRACT(YEAR FROM a.date_signature) = :annee")
        params["annee"] = annee

    where = " AND ".join(conditions)

    total = db.execute(
        text(f"""
            SELECT COUNT(*) FROM attributions a
            LEFT JOIN appels_offres ao ON ao.id = a.ao_id
            WHERE {where}
        """), params
    ).scalar()

    rows = db.execute(text(f"""
        SELECT
            a.id, a.attributaire, a.montant_final, a.date_signature, a.source_quotidien,
            ao.id AS ao_id, ao.titre, ao.secteur, ao.autorite_contractante,
            ao.montant_estime, ao.type_procedure
        FROM attributions a
        LEFT JOIN appels_offres ao ON ao.id = a.ao_id
        WHERE {where}
        ORDER BY a.date_signature DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """), params).fetchall()

    return open_response({
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    (total + per_page - 1) // per_page,
        "source":   "NetSync Gov — Résultats publiés dans le Quotidien DGCMEF",
        "attributions": [
            {
                "id":                   str(r.id),
                "attributaire":         r.attributaire,
                "montant_final":        r.montant_final,
                "date_signature":       r.date_signature.isoformat() if r.date_signature else None,
                "source_quotidien":     r.source_quotidien,
                "ao": {
                    "id":              str(r.ao_id) if r.ao_id else None,
                    "titre":           r.titre,
                    "secteur":         r.secteur,
                    "autorite":        r.autorite_contractante,
                    "montant_estime":  r.montant_estime,
                    "type_procedure":  r.type_procedure,
                },
                "delta_montant": (
                    r.montant_final - r.montant_estime
                    if r.montant_final and r.montant_estime else None
                ),
            }
            for r in rows
        ],
    })


@router.get("/attributions/top-attributaires")
def top_attributaires(
    limite: int = Query(10, ge=1, le=50),
    annee: Optional[int] = None,
    secteur: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Classement des entreprises ayant décroché le plus de marchés.
    Données de transparence — accessibles sans inscription.
    """
    conditions = ["1=1"]
    params: dict = {"limite": limite}

    if annee:
        conditions.append("EXTRACT(YEAR FROM a.date_signature) = :annee")
        params["annee"] = annee
    if secteur:
        conditions.append("ao.secteur = :secteur")
        params["secteur"] = secteur

    where = " AND ".join(conditions)

    rows = db.execute(text(f"""
        SELECT
            a.attributaire,
            COUNT(*)            AS nb_marches,
            SUM(a.montant_final) AS montant_total,
            AVG(a.montant_final) AS montant_moyen,
            COUNT(DISTINCT ao.secteur) AS nb_secteurs
        FROM attributions a
        LEFT JOIN appels_offres ao ON ao.id = a.ao_id
        WHERE {where}
        GROUP BY a.attributaire
        ORDER BY nb_marches DESC
        LIMIT :limite
    """), params).fetchall()

    return open_response({
        "classement": [
            {
                "rang":          i + 1,
                "attributaire":  r.attributaire,
                "nb_marches":    r.nb_marches,
                "montant_total": int(r.montant_total) if r.montant_total else None,
                "montant_moyen": int(r.montant_moyen) if r.montant_moyen else None,
                "nb_secteurs":   r.nb_secteurs,
            }
            for i, r in enumerate(rows)
        ],
        "source": "NetSync Gov — Données DGCMEF Burkina Faso",
    })


# ── Données géographiques ─────────────────────────────────────────────────────

@router.get("/carte")
def donnees_carte(
    periode: str = Query("12m"),
    db: Session = Depends(get_db),
):
    """
    Données agrégées par région pour la carte interactive.
    Basé sur les mentions de villes/régions dans les titres et descriptions des AOs.
    """
    debut = date.today() - timedelta(days=365 if periode == "12m" else 180)

    # Recherche par mentions de régions dans les AOs
    REGIONS = {
        "Ouagadougou":   ["ouagadougou", "ouaga", "kadiogo"],
        "Bobo-Dioulasso": ["bobo", "bobo-dioulasso", "houet"],
        "Koudougou":     ["koudougou", "boulkiemdé"],
        "Banfora":       ["banfora", "comoé"],
        "Dédougou":      ["dédougou", "mouhoun"],
        "Fada N'Gourma": ["fada", "gnagna", "gourma"],
        "Kaya":          ["kaya", "sanmatenga"],
        "Tenkodogo":     ["tenkodogo", "boulgou"],
        "Dori":          ["dori", "séno"],
        "Ouahigouya":    ["ouahigouya", "yatenga"],
    }

    result = []
    for region, mots_cles in REGIONS.items():
        pattern = "|".join(mots_cles)
        count = db.execute(text("""
            SELECT COUNT(*) FROM appels_offres
            WHERE date_publication >= :debut
              AND (
                LOWER(titre) ~* :pattern
                OR LOWER(COALESCE(description, '')) ~* :pattern
                OR LOWER(COALESCE(autorite_contractante, '')) ~* :pattern
              )
        """), {"debut": debut, "pattern": pattern}).scalar()

        if count > 0:
            result.append({"region": region, "nb_ao": count})

    return open_response({
        "periode": periode,
        "regions": sorted(result, key=lambda x: x["nb_ao"], reverse=True),
        "note": "Comptage basé sur les mentions de régions dans les titres et autorités des AOs.",
    })


# ── Open Data API ─────────────────────────────────────────────────────────────

@router.get("/opendata/stats")
def opendata_stats(db: Session = Depends(get_db)):
    """
    Statistiques globales — endpoint Open Data sans restriction.
    Idéal pour les widgets externes, tableaux de bord citoyens, presse.
    """
    total_ao      = db.execute(text("SELECT COUNT(*) FROM appels_offres")).scalar()
    ao_ouverts    = db.execute(text("SELECT COUNT(*) FROM appels_offres WHERE statut='ouvert'")).scalar()
    total_attr    = db.execute(text("SELECT COUNT(*) FROM attributions")).scalar()
    montant_total = db.execute(text("SELECT SUM(montant_final) FROM attributions")).scalar()
    ce_mois       = db.execute(text("""
        SELECT COUNT(*) FROM appels_offres
        WHERE date_publication >= DATE_TRUNC('month', NOW())
    """)).scalar()

    top_secteur = db.execute(text("""
        SELECT secteur, COUNT(*) as nb FROM appels_offres
        WHERE date_publication >= NOW() - INTERVAL '30 days'
          AND secteur IS NOT NULL
        GROUP BY secteur ORDER BY nb DESC LIMIT 1
    """)).fetchone()

    return open_response({
        "total_ao_indexes":           total_ao,
        "ao_ouverts":                 ao_ouverts,
        "ao_ce_mois":                 ce_mois,
        "total_attributions_indexees": total_attr,
        "montant_total_attribue_fcfa": int(montant_total) if montant_total else None,
        "top_secteur_30j":            top_secteur.secteur if top_secteur else None,
        "source":                     "NetSync Gov — gov.netsync.bf",
        "licence":                    "Open Data — Usage libre avec attribution",
        "mis_a_jour":                 date.today().isoformat(),
        "contact":                    "contact@netsync.bf",
    })


@router.get("/opendata/schema")
def opendata_schema():
    """
    Documentation du schéma de données Open Data NetSync Gov.
    """
    return open_response({
        "version":   "1.0",
        "base_url":  "https://api.gov.netsync.bf/api/v1/transparence",
        "licence":   "Open Data BF — Attribution requise",
        "contact":   "contact@netsync.bf",
        "endpoints": {
            "/aos":                     "Liste des appels d'offres (filtres: q, secteur, statut, page)",
            "/aos/{id}":                "Fiche complète d'un AO",
            "/attributions":            "Marchés attribués (filtres: q, attributaire, secteur, annee)",
            "/attributions/top-attributaires": "Classement des attributaires",
            "/carte":                   "Données par région BF",
            "/opendata/stats":          "Statistiques globales",
            "/opendata/schema":         "Ce document",
        },
        "champs_ao": {
            "id":               "UUID unique de l'AO",
            "reference":        "Référence officielle DGCMEF",
            "titre":            "Titre du marché",
            "autorite":         "Autorité contractante",
            "secteur":          "Secteur : btp|informatique|sante|agriculture|conseil|...",
            "type_procedure":   "ouvert|restreint|dpx|ami|rfp",
            "statut":           "ouvert|cloture|attribue",
            "source":           "dgcmef|cci_bf|undp|bm_step",
            "date_publication": "ISO 8601",
            "date_cloture":     "ISO 8601",
            "montant_estime":   "Montant en FCFA (entier)",
            "pdf_url":          "URL du PDF source DGCMEF",
            "url_fiche":        "URL de la fiche NetSync Gov",
        },
    })
