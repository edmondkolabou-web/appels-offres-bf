"""
NetSync Gov — Router : Authentification
POST /auth/register     → créer un compte
POST /auth/login        → obtenir un JWT
GET  /auth/me           → profil courant
PUT  /auth/me           → mettre à jour le profil
POST /auth/verify-email → vérifier l'email
POST /auth/forgot-password   → demander un lien de réinitialisation
POST /auth/reset-password    → réinitialiser le mot de passe
"""
import secrets

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Abonne, PreferenceAlerte
from backend.schemas import RegisterIn, LoginIn, TokenOut, AbonneOut, AbonneUpdate
from backend.security import (hash_password, verify_password,
                      create_access_token, get_current_abonne)

router = APIRouter()

# Token de vérification email (en prod : stocker en Redis avec TTL)
_pending_tokens: dict = {}


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Créer un nouveau compte abonné."""
    # Vérifier unicité email
    if db.query(Abonne).filter(Abonne.email == body.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte existe déjà avec cet email",
        )

    abonne = Abonne(
        email=body.email,
        password_hash=hash_password(body.password),
        prenom=body.prenom,
        nom=body.nom,
        entreprise=body.entreprise,
        whatsapp=body.whatsapp,
        plan=body.plan,
        email_verifie=False,
        actif=True,
    )
    db.add(abonne)
    db.flush()

    # Créer préférences d'alertes par défaut si secteurs fournis
    if body.secteurs:
        pref = PreferenceAlerte(
            abonne_id=abonne.id,
            secteurs=body.secteurs,
            canal="les_deux",
            rappel_j3=True,
            actif=True,
        )
        db.add(pref)

    db.commit()
    db.refresh(abonne)

    # Envoyer email de vérification en arrière-plan
    token = secrets.token_urlsafe(32)
    _pending_tokens[token] = str(abonne.id)
    background_tasks.add_task(_send_verification_email, abonne.email, token)

    access_token = create_access_token(str(abonne.id))
    return TokenOut(
        access_token=access_token,
        abonne_id=str(abonne.id),
        plan=abonne.plan,
    )


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    """Authentification — retourne un JWT."""
    abonne = db.query(Abonne).filter(Abonne.email == body.email).first()
    if not abonne or not abonne.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    if not verify_password(body.password, abonne.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    if not abonne.actif:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé — contactez le support",
        )

    return TokenOut(
        access_token=create_access_token(str(abonne.id)),
        abonne_id=str(abonne.id),
        plan=abonne.plan,
    )


@router.get("/me", response_model=AbonneOut)
def me(current: Abonne = Depends(get_current_abonne)):
    """Retourne le profil de l'abonné connecté."""
    return AbonneOut.from_orm_compat(current)


@router.put("/me", response_model=AbonneOut)
def update_me(
    body: AbonneUpdate,
    db: Session = Depends(get_db),
    current: Abonne = Depends(get_current_abonne),
):
    """Met à jour les informations du profil."""
    if body.prenom is not None:
        current.prenom = body.prenom
    if body.nom is not None:
        current.nom = body.nom
    if body.entreprise is not None:
        current.entreprise = body.entreprise
    if body.whatsapp is not None:
        current.whatsapp = body.whatsapp
    db.commit()
    db.refresh(current)
    return AbonneOut.from_orm_compat(current)


@router.post("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    """Valide l'email d'un abonné via le token envoyé par email."""
    abonne_id = _pending_tokens.pop(token, None)
    if not abonne_id:
        raise HTTPException(status_code=400, detail="Token invalide ou expiré")
    abonne = db.get(Abonne, abonne_id)
    if not abonne:
        raise HTTPException(status_code=404, detail="Abonné introuvable")
    abonne.email_verifie = True
    db.commit()
    return {"message": "Email vérifié avec succès"}


@router.post("/forgot-password")
def forgot_password(email: str, background_tasks: BackgroundTasks,
                    db: Session = Depends(get_db)):
    """Envoie un email de réinitialisation du mot de passe."""
    # Toujours retourner 200 pour ne pas révéler si l'email existe
    abonne = db.query(Abonne).filter(Abonne.email == email).first()
    if abonne:
        token = secrets.token_urlsafe(32)
        _pending_tokens[f"reset:{token}"] = str(abonne.id)
        background_tasks.add_task(_send_reset_email, email, token)
    return {"message": "Si cet email existe, un lien de réinitialisation a été envoyé"}


@router.post("/reset-password")
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    """Réinitialise le mot de passe via un token valide."""
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Mot de passe trop court (8 caractères minimum)")
    key = f"reset:{token}"
    abonne_id = _pending_tokens.pop(key, None)
    if not abonne_id:
        raise HTTPException(status_code=400, detail="Token invalide ou expiré")
    abonne = db.get(Abonne, abonne_id)
    if not abonne:
        raise HTTPException(status_code=404, detail="Abonné introuvable")
    abonne.password_hash = hash_password(new_password)
    db.commit()
    return {"message": "Mot de passe réinitialisé avec succès"}


def _send_verification_email(email: str, token: str):
    """Envoie l'email de vérification via Resend (simulation en dev)."""
    verify_url = f"https://gov.netsync.bf/verify?token={token}"
    import logging
    logging.getLogger("netsync.auth").info(f"[EMAIL] Vérification → {email} | {verify_url}")
    # En production : appel Resend API


def _send_reset_email(email: str, token: str):
    """Envoie l'email de réinitialisation via Resend."""
    reset_url = f"https://gov.netsync.bf/reset-password?token={token}"
    import logging
    logging.getLogger("netsync.auth").info(f"[EMAIL] Reset password → {email} | {reset_url}")
