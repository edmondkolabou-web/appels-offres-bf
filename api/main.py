"""
API REST — Appels Offres BF
Lancer : uvicorn api.main:app --reload  (depuis la racine du projet)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from database.database import get_connection, init_db
from alertes.alertes import envoyer_email_test, traiter_alertes

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Démarrage ──────────────────────────────────────────────────
    init_db()
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM offres").fetchone()[0]
    conn.close()
    if count == 0:
        print("Base vide — lancement du scraping initial...")
        from scraper.scraper import lancer_scraping
        lancer_scraping()
    else:
        print(f"Base OK — {count} offre(s) en base.")
    yield
    # ── Arrêt (rien à nettoyer pour l'instant) ─────────────────────


app = FastAPI(
    title="Appels Offres BF",
    description="API d'agrégation des appels d'offres publics et privés du Burkina Faso",
    version="1.0.0",
    lifespan=lifespan,
)


def row_to_dict(row) -> dict:
    return dict(row)


# ---------------------------------------------------------------------------
# GET /  → interface web
# GET /api → info JSON
# ---------------------------------------------------------------------------

@app.get("/")
def accueil():
    return FileResponse(os.path.join(TEMPLATES_DIR, "index.html"))

@app.get("/api")
def api_info():
    return {
        "projet": "Appels Offres BF",
        "description": "Agrégation des appels d'offres publics et privés du Burkina Faso",
        "version": "1.0.0",
        "sources": ["lesaffairesbf.com", "arcop.bf"],
        "routes": {
            "GET /offres":              "Liste paginée des offres",
            "GET /offres/{id}":         "Détail d'une offre",
            "GET /offres/search?q=mot": "Recherche par mot-clé",
            "GET /stats":               "Statistiques globales",
        },
    }


# ---------------------------------------------------------------------------
# GET /offres/search   (doit être AVANT /offres/{id} pour éviter collision)
# ---------------------------------------------------------------------------

@app.get("/offres/search")
def rechercher_offres(
    q: str = Query(..., min_length=2, description="Mot-clé à rechercher dans le titre"),
    page: int = Query(1, ge=1),
    limite: int = Query(10, ge=1, le=100),
):
    offset = (page - 1) * limite
    pattern = f"%{q}%"

    conn = get_connection()
    total = conn.execute(
        "SELECT COUNT(*) FROM offres WHERE titre LIKE ?", (pattern,)
    ).fetchone()[0]

    rows = conn.execute(
        """
        SELECT id, titre, source, type_offre, secteur,
               date_publication, date_limite, organisme, statut, url_source
        FROM offres
        WHERE titre LIKE ?
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        (pattern, limite, offset),
    ).fetchall()
    conn.close()

    return {
        "requete": q,
        "total": total,
        "page": page,
        "limite": limite,
        "pages_total": max(1, -(-total // limite)),  # ceil division
        "resultats": [row_to_dict(r) for r in rows],
    }


# ---------------------------------------------------------------------------
# GET /offres
# ---------------------------------------------------------------------------

@app.get("/offres")
def lister_offres(
    page: int = Query(1, ge=1),
    limite: int = Query(10, ge=1, le=100),
    source: str | None = Query(None, description="Filtrer par source"),
    statut: str | None = Query(None, description="Filtrer par statut (ouvert/clos/annule)"),
):
    offset = (page - 1) * limite

    where_clauses = []
    params: list = []

    if source:
        where_clauses.append("source = ?")
        params.append(source)
    if statut:
        where_clauses.append("statut = ?")
        params.append(statut)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    conn = get_connection()
    total = conn.execute(
        f"SELECT COUNT(*) FROM offres {where_sql}", params
    ).fetchone()[0]

    rows = conn.execute(
        f"""
        SELECT id, titre, source, type_offre, secteur,
               date_publication, date_limite, organisme, statut, url_source
        FROM offres
        {where_sql}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        params + [limite, offset],
    ).fetchall()
    conn.close()

    return {
        "total": total,
        "page": page,
        "limite": limite,
        "pages_total": max(1, -(-total // limite)),
        "offres": [row_to_dict(r) for r in rows],
    }


# ---------------------------------------------------------------------------
# GET /offres/{id}
# ---------------------------------------------------------------------------

@app.get("/offres/{offre_id}")
def detail_offre(offre_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM offres WHERE id = ?", (offre_id,)
    ).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Offre {offre_id} introuvable")

    return row_to_dict(row)


# ---------------------------------------------------------------------------
# GET /stats
# ---------------------------------------------------------------------------

@app.get("/stats")
def statistiques():
    conn = get_connection()

    total = conn.execute("SELECT COUNT(*) FROM offres").fetchone()[0]

    par_source = {
        row["source"]: row["nb"]
        for row in conn.execute(
            "SELECT source, COUNT(*) as nb FROM offres GROUP BY source ORDER BY nb DESC"
        ).fetchall()
    }

    par_statut = {
        row["statut"]: row["nb"]
        for row in conn.execute(
            "SELECT statut, COUNT(*) as nb FROM offres GROUP BY statut"
        ).fetchall()
    }

    derniere_maj = conn.execute(
        "SELECT MAX(created_at) as maj FROM offres"
    ).fetchone()["maj"]

    conn.close()

    return {
        "total_offres": total,
        "par_source": par_source,
        "par_statut": par_statut,
        "derniere_mise_a_jour": derniere_maj,
    }


# ---------------------------------------------------------------------------
# GET /alertes/test   — doit être AVANT /alertes/{id} si on en ajoute
# ---------------------------------------------------------------------------

@app.get("/alertes/test")
def test_alerte(
    email: str = Query(..., description="Adresse email de test"),
):
    """
    Envoie un email de test avec les 3 dernières offres en base.
    Si SMTP_USER/SMTP_PASS ne sont pas configurés, simule l'envoi
    et retourne le statut 'simulé'.
    """
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="Adresse email invalide")

    resultat = envoyer_email_test(email)
    return resultat


# ---------------------------------------------------------------------------
# POST /alertes/run   — déclenche le traitement complet des alertes
# ---------------------------------------------------------------------------

@app.post("/alertes/run")
def run_alertes():
    """
    Déclenche manuellement le traitement des alertes :
    vérifie les offres du jour et envoie les emails aux utilisateurs concernés.
    En production, cette route serait appelée par un cron.
    """
    bilan = traiter_alertes()
    return bilan
