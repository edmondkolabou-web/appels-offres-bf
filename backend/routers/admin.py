"""
NetSync Gov — Router : Administration (routes protégées admin)
POST /admin/pipeline/run    → déclencher le pipeline manuellement
GET  /admin/pipeline/logs   → historique des runs pipeline
GET  /admin/stats           → statistiques globales de la plateforme
GET  /admin/abonnes         → liste des abonnés
PUT  /admin/abonnes/{id}/plan → changer le plan d'un abonné manuellement
POST /admin/alertes/rappels → déclencher les rappels J-3 manuellement
"""
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Abonne, AppelOffre, EnvoiAlerte, PipelineLog
from backend.schemas import PipelineLogOut, StatsOut
from backend.security import require_admin

router = APIRouter()


@router.post("/pipeline/run")
def run_pipeline_manual(
    current: Abonne = Depends(require_admin),
):
    """
    Déclenche le pipeline PDF manuellement via Celery.
    Utile pour forcer un re-traitement ou tester sans attendre 7h00.
    """
    try:
        from pipeline import run_pipeline
        task = run_pipeline.delay()
        return {
            "message": "Pipeline déclenché",
            "task_id": task.id,
            "status": "queued",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur déclenchement pipeline : {e}")


@router.get("/pipeline/logs", response_model=list[PipelineLogOut])
def get_pipeline_logs(
    limit:   int     = Query(20, ge=1, le=100),
    db:      Session = Depends(get_db),
    current: Abonne  = Depends(require_admin),
):
    """Historique des runs du pipeline PDF avec statistiques."""
    logs = (
        db.query(PipelineLog)
        .order_by(PipelineLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [PipelineLogOut.model_validate(l) for l in logs]


@router.get("/stats", response_model=StatsOut)
def get_stats(
    db:      Session = Depends(get_db),
    current: Abonne  = Depends(require_admin),
):
    """Statistiques globales de la plateforme."""
    today      = date.today()
    mois_debut = today.replace(day=1)
    sept_jours = today - timedelta(days=7)

    total_ao     = db.query(func.count(AppelOffre.id)).scalar() or 0
    ao_ouverts   = db.query(func.count(AppelOffre.id)).filter(AppelOffre.statut == "ouvert").scalar() or 0
    ao_ce_mois   = (db.query(func.count(AppelOffre.id))
                     .filter(AppelOffre.date_publication >= mois_debut).scalar() or 0)
    total_abonnes = db.query(func.count(Abonne.id)).scalar() or 0
    abonnes_pro   = (db.query(func.count(Abonne.id))
                      .filter(Abonne.plan.in_(["pro", "equipe"])).scalar() or 0)
    alertes_7j    = (db.query(func.count(EnvoiAlerte.id))
                      .filter(EnvoiAlerte.created_at >= sept_jours,
                              EnvoiAlerte.statut == "envoye").scalar() or 0)

    return StatsOut(
        total_ao=total_ao,
        ao_ouverts=ao_ouverts,
        ao_ce_mois=ao_ce_mois,
        total_abonnes=total_abonnes,
        abonnes_pro=abonnes_pro,
        alertes_envoyees_7j=alertes_7j,
    )


@router.get("/abonnes")
def list_abonnes(
    plan:    str = Query(None, description="Filtrer par plan"),
    page:    int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db:      Session = Depends(get_db),
    current: Abonne  = Depends(require_admin),
):
    """Liste paginée des abonnés avec leurs métadonnées."""
    q = db.query(Abonne)
    if plan:
        q = q.filter(Abonne.plan == plan)
    total = q.count()
    abonnes = q.order_by(Abonne.created_at.desc()).offset((page-1)*per_page).limit(per_page).all()
    return {
        "total": total,
        "page": page,
        "items": [
            {
                "id": str(a.id),
                "email": a.email,
                "prenom": a.prenom,
                "nom": a.nom,
                "plan": a.plan,
                "plan_expire_le": a.plan_expire_le.isoformat() if a.plan_expire_le else None,
                "actif": a.actif,
                "created_at": a.created_at.isoformat(),
            }
            for a in abonnes
        ],
    }


@router.put("/abonnes/{abonne_id}/plan")
def update_abonne_plan(
    abonne_id: UUID,
    plan:      str,
    expire_le: date = None,
    db:        Session = Depends(get_db),
    current:   Abonne  = Depends(require_admin),
):
    """Modifie manuellement le plan d'un abonné (support client)."""
    abonne = db.get(Abonne, abonne_id)
    if not abonne:
        raise HTTPException(status_code=404, detail="Abonné introuvable")
    if plan not in ("gratuit", "pro", "equipe"):
        raise HTTPException(status_code=400, detail="Plan invalide")
    abonne.plan = plan
    abonne.plan_expire_le = expire_le
    db.commit()
    return {"message": f"Plan de {abonne.email} mis à jour → {plan}"}


@router.post("/alertes/rappels")
def run_rappels_j3(
    current: Abonne = Depends(require_admin),
):
    """Déclenche manuellement les rappels J-3 via Celery."""
    try:
        from pipeline import run_rappels_j3
        task = run_rappels_j3.delay()
        return {"message": "Rappels J-3 déclenchés", "task_id": task.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur : {e}")
