"""
NetSync Gov — Router : Favoris
GET    /favoris           → lister mes favoris
POST   /favoris           → ajouter un AO aux favoris
DELETE /favoris/{ao_id}  → retirer un AO des favoris
PUT    /favoris/{ao_id}  → mettre à jour la note d'un favori
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Abonne, AppelOffre, Favori
from backend.schemas import FavoriIn, FavoriOut
from backend.security import get_current_abonne

router = APIRouter()


@router.get("", response_model=list[FavoriOut])
def list_favoris(
    db:      Session = Depends(get_db),
    current: Abonne  = Depends(get_current_abonne),
):
    """Liste les AOs sauvegardés par l'abonné connecté."""
    return [FavoriOut.model_validate(f)
            for f in db.query(Favori)
                       .filter(Favori.abonne_id == current.id)
                       .order_by(Favori.created_at.desc())
                       .all()]


@router.post("", response_model=FavoriOut, status_code=status.HTTP_201_CREATED)
def add_favori(
    body:    FavoriIn,
    db:      Session = Depends(get_db),
    current: Abonne  = Depends(get_current_abonne),
):
    """Ajouter un AO aux favoris."""
    ao = db.get(AppelOffre, body.ao_id)
    if not ao:
        raise HTTPException(status_code=404, detail="Appel d'offres introuvable")

    # Vérifier doublon
    existing = (
        db.query(Favori)
        .filter(Favori.abonne_id == current.id, Favori.ao_id == body.ao_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="AO déjà dans les favoris")

    favori = Favori(abonne_id=current.id, ao_id=body.ao_id, note=body.note)
    db.add(favori)
    db.commit()
    db.refresh(favori)
    return FavoriOut.model_validate(favori)


@router.put("/{ao_id}", response_model=FavoriOut)
def update_favori_note(
    ao_id:   UUID,
    note:    str,
    db:      Session = Depends(get_db),
    current: Abonne  = Depends(get_current_abonne),
):
    """Mettre à jour la note privée d'un favori."""
    favori = (
        db.query(Favori)
        .filter(Favori.abonne_id == current.id, Favori.ao_id == ao_id)
        .first()
    )
    if not favori:
        raise HTTPException(status_code=404, detail="Favori introuvable")
    favori.note = note
    db.commit()
    db.refresh(favori)
    return FavoriOut.model_validate(favori)


@router.delete("/{ao_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favori(
    ao_id:   UUID,
    db:      Session = Depends(get_db),
    current: Abonne  = Depends(get_current_abonne),
):
    """Retirer un AO des favoris."""
    favori = (
        db.query(Favori)
        .filter(Favori.abonne_id == current.id, Favori.ao_id == ao_id)
        .first()
    )
    if not favori:
        raise HTTPException(status_code=404, detail="Favori introuvable")
    db.delete(favori)
    db.commit()
