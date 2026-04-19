"""
NetSync Gov — Router : Préférences d'alertes
GET    /alertes          → lister mes alertes
POST   /alertes          → créer une alerte
PUT    /alertes/{id}     → modifier une alerte
DELETE /alertes/{id}     → supprimer une alerte
POST   /alertes/{id}/toggle → activer/désactiver
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Abonne, PreferenceAlerte
from backend.schemas import AlerteIn, AlerteOut, AlerteUpdate
from backend.security import get_current_abonne

router = APIRouter()

MAX_ALERTES_GRATUIT = 1
MAX_ALERTES_PRO     = 10


def _get_alerte_or_404(alerte_id: UUID, abonne_id, db: Session) -> PreferenceAlerte:
    alerte = db.get(PreferenceAlerte, alerte_id)
    if not alerte or str(alerte.abonne_id) != str(abonne_id):
        raise HTTPException(status_code=404, detail="Alerte introuvable")
    return alerte


@router.get("", response_model=list[AlerteOut])
def list_alertes(
    db:      Session = Depends(get_db),
    current: Abonne  = Depends(get_current_abonne),
):
    """Liste toutes les alertes configurées par l'abonné connecté."""
    return [AlerteOut.model_validate(a)
            for a in db.query(PreferenceAlerte)
                       .filter(PreferenceAlerte.abonne_id == current.id)
                       .order_by(PreferenceAlerte.created_at.desc())
                       .all()]


@router.post("", response_model=AlerteOut, status_code=status.HTTP_201_CREATED)
def create_alerte(
    body:    AlerteIn,
    db:      Session = Depends(get_db),
    current: Abonne  = Depends(get_current_abonne),
):
    """Créer une nouvelle alerte. Plan Gratuit : maximum 1 alerte."""
    nb_existing = (
        db.query(PreferenceAlerte)
        .filter(PreferenceAlerte.abonne_id == current.id)
        .count()
    )
    limit = MAX_ALERTES_GRATUIT if not current.est_pro else MAX_ALERTES_PRO
    if nb_existing >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Limite d'alertes atteinte ({limit}). Passez au plan Pro pour en ajouter davantage.",
        )

    alerte = PreferenceAlerte(
        abonne_id=current.id,
        secteurs=body.secteurs,
        mots_cles=body.mots_cles,
        sources=body.sources,
        canal=body.canal,
        rappel_j3=body.rappel_j3,
        actif=True,
    )
    db.add(alerte)
    db.commit()
    db.refresh(alerte)
    return AlerteOut.model_validate(alerte)


@router.put("/{alerte_id}", response_model=AlerteOut)
def update_alerte(
    alerte_id: UUID,
    body:      AlerteUpdate,
    db:        Session = Depends(get_db),
    current:   Abonne  = Depends(get_current_abonne),
):
    """Modifier une alerte existante."""
    alerte = _get_alerte_or_404(alerte_id, current.id, db)
    if body.secteurs  is not None: alerte.secteurs  = body.secteurs
    if body.mots_cles is not None: alerte.mots_cles = body.mots_cles
    if body.sources   is not None: alerte.sources   = body.sources
    if body.canal     is not None: alerte.canal     = body.canal
    if body.rappel_j3 is not None: alerte.rappel_j3 = body.rappel_j3
    if body.actif     is not None: alerte.actif     = body.actif
    db.commit()
    db.refresh(alerte)
    return AlerteOut.model_validate(alerte)


@router.post("/{alerte_id}/toggle", response_model=AlerteOut)
def toggle_alerte(
    alerte_id: UUID,
    db:        Session = Depends(get_db),
    current:   Abonne  = Depends(get_current_abonne),
):
    """Active ou désactive une alerte."""
    alerte = _get_alerte_or_404(alerte_id, current.id, db)
    alerte.actif = not alerte.actif
    db.commit()
    db.refresh(alerte)
    return AlerteOut.model_validate(alerte)


@router.delete("/{alerte_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alerte(
    alerte_id: UUID,
    db:        Session = Depends(get_db),
    current:   Abonne  = Depends(get_current_abonne),
):
    """Supprimer une alerte."""
    alerte = _get_alerte_or_404(alerte_id, current.id, db)
    db.delete(alerte)
    db.commit()
