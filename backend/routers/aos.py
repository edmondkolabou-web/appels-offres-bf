"""
NetSync Gov — Router : Appels d'offres
GET  /aos                → liste paginée + filtres + full-text search
GET  /aos/{id}           → détail complet
GET  /aos/today          → AOs publiés aujourd'hui
GET  /aos/urgent         → AOs clôturant dans <= 3 jours
GET  /aos/secteurs        → liste des secteurs disponibles
"""
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Abonne, AppelOffre
from backend.schemas import AODetail, AOFilters, AOListItem, AOListResponse
from backend.security import get_current_abonne

router = APIRouter()


def _apply_filters(query, filters: AOFilters):
    """Applique les filtres sur la requête SQLAlchemy."""
    # Recherche full-text
    if filters.q:
        tsq = func.plainto_tsquery("french", filters.q)
        query = query.filter(AppelOffre.search_vector.op("@@")(tsq))
        query = query.order_by(func.ts_rank(AppelOffre.search_vector, tsq).desc())
    else:
        query = query.order_by(AppelOffre.date_publication.desc(), AppelOffre.created_at.desc())

    if filters.secteur:
        query = query.filter(AppelOffre.secteur == filters.secteur)
    if filters.statut:
        query = query.filter(AppelOffre.statut == filters.statut)
    if filters.source:
        query = query.filter(AppelOffre.source == filters.source)
    if filters.type_procedure:
        query = query.filter(AppelOffre.type_procedure == filters.type_procedure)
    if filters.date_debut:
        query = query.filter(AppelOffre.date_publication >= filters.date_debut)
    if filters.date_fin:
        query = query.filter(AppelOffre.date_publication <= filters.date_fin)
    if filters.montant_min:
        query = query.filter(AppelOffre.montant_estime >= filters.montant_min)
    if filters.montant_max:
        query = query.filter(AppelOffre.montant_estime <= filters.montant_max)
    if filters.urgent_only:
        deadline = date.today() + timedelta(days=3)
        query = query.filter(
            AppelOffre.date_cloture.isnot(None),
            AppelOffre.date_cloture <= deadline,
            AppelOffre.date_cloture >= date.today(),
        )
    return query


@router.get("", response_model=AOListResponse)
def list_aos(
    q:              Optional[str]  = Query(None, description="Recherche full-text"),
    secteur:        Optional[str]  = Query(None),
    statut:         Optional[str]  = Query("ouvert"),
    source:         Optional[str]  = Query(None),
    type_procedure: Optional[str]  = Query(None),
    date_debut:     Optional[date] = Query(None),
    date_fin:       Optional[date] = Query(None),
    montant_min:    Optional[int]  = Query(None),
    montant_max:    Optional[int]  = Query(None),
    urgent_only:    bool           = Query(False),
    page:           int            = Query(1, ge=1),
    per_page:       int            = Query(20, ge=1, le=100),
    db:             Session        = Depends(get_db),
    current:        Abonne         = Depends(get_current_abonne),
):
    """
    Liste des AOs avec filtres, recherche full-text et pagination.
    Plan Gratuit : limité à 3 consultations/jour.
    """
    # Contrôle freemium
    if not current.est_pro:
        if current.ao_consultes_auj >= 3:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Limite journalière atteinte (3 AO/jour). Passez au plan Pro.",
            )

    filters = AOFilters(
        q=q, secteur=secteur, statut=statut, source=source,
        type_procedure=type_procedure, date_debut=date_debut,
        date_fin=date_fin, montant_min=montant_min, montant_max=montant_max,
        urgent_only=urgent_only, page=page, per_page=per_page,
    )

    base_q = db.query(AppelOffre)
    base_q = _apply_filters(base_q, filters)

    total   = base_q.count()
    offset  = (page - 1) * per_page
    items   = base_q.offset(offset).limit(per_page).all()

    return AOListResponse(
        items=[AOListItem.model_validate(ao) for ao in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=max(1, (total + per_page - 1) // per_page),
    )


@router.get("/today", response_model=AOListResponse)
def aos_today(
    page:    int     = Query(1, ge=1),
    per_page: int    = Query(20, ge=1, le=50),
    db:      Session = Depends(get_db),
    current: Abonne  = Depends(get_current_abonne),
):
    """AOs publiés aujourd'hui — shortcut pour le dashboard."""
    q = db.query(AppelOffre).filter(
        AppelOffre.date_publication == date.today()
    ).order_by(AppelOffre.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return AOListResponse(
        items=[AOListItem.model_validate(ao) for ao in items],
        total=total, page=page, per_page=per_page,
        pages=max(1, (total + per_page - 1) // per_page),
    )


@router.get("/urgent", response_model=AOListResponse)
def aos_urgent(
    db:      Session = Depends(get_db),
    current: Abonne  = Depends(get_current_abonne),
):
    """AOs dont la clôture est dans <= 3 jours."""
    deadline = date.today() + timedelta(days=3)
    items = (
        db.query(AppelOffre)
        .filter(
            AppelOffre.statut == "ouvert",
            AppelOffre.date_cloture.isnot(None),
            AppelOffre.date_cloture >= date.today(),
            AppelOffre.date_cloture <= deadline,
        )
        .order_by(AppelOffre.date_cloture.asc())
        .all()
    )
    return AOListResponse(
        items=[AOListItem.model_validate(ao) for ao in items],
        total=len(items), page=1, per_page=50, pages=1,
    )


@router.get("/secteurs")
def list_secteurs(db: Session = Depends(get_db)):
    """Liste des secteurs présents en base avec leur nombre d'AOs."""
    rows = (
        db.query(AppelOffre.secteur, func.count(AppelOffre.id).label("nb"))
        .filter(AppelOffre.statut == "ouvert")
        .group_by(AppelOffre.secteur)
        .order_by(func.count(AppelOffre.id).desc())
        .all()
    )
    return [{"secteur": r.secteur, "nb_ao": r.nb} for r in rows]


@router.get("/{ao_id}", response_model=AODetail)
def get_ao(
    ao_id:   UUID,
    db:      Session = Depends(get_db),
    current: Abonne  = Depends(get_current_abonne),
):
    """Détail complet d'un appel d'offres."""
    ao = db.get(AppelOffre, ao_id)
    if not ao:
        raise HTTPException(status_code=404, detail="Appel d'offres introuvable")

    # Freemium : compter la consultation
    if not current.est_pro:
        if current.ao_consultes_auj >= 3:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Limite journalière atteinte. Passez au plan Pro.",
            )
        current.ao_consultes_auj += 1
        db.commit()

    return AODetail.model_validate(ao)


@router.get("/{ao_id}/pdf")
def download_ao_pdf(
    ao_id:   UUID,
    db:      Session = Depends(get_db),
    current: Abonne  = Depends(get_current_abonne),
):
    """Télécharge le PDF source d'un AO (proxy DGCMEF avec cache local)."""
    import os
    from fastapi.responses import FileResponse, RedirectResponse

    ao = db.get(AppelOffre, ao_id)
    if not ao:
        raise HTTPException(status_code=404, detail="Appel d'offres introuvable")

    if not ao.pdf_url:
        raise HTTPException(status_code=404, detail="Pas de PDF disponible pour cet AO")

    # Vérifier le cache local
    if ao.numero_quotidien:
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "static", "pdfs")
        cached_file = os.path.join(cache_dir, f"quotidien_{ao.numero_quotidien}.pdf")
        if os.path.exists(cached_file):
            return FileResponse(
                cached_file,
                media_type="application/pdf",
                filename=f"DGCMEF_Quotidien_{ao.numero_quotidien}.pdf"
            )

    # Fallback : rediriger vers l'URL source
    return RedirectResponse(url=ao.pdf_url, status_code=302)
