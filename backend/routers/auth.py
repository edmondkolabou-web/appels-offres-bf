"""
NetSync Gov — Router : Authentification SaaS complète
POST /auth/register         → créer un compte
POST /auth/login            → access + refresh token
POST /auth/refresh          → renouveler l'access token
POST /auth/logout           → révoquer le refresh token
GET  /auth/me               → profil courant
PUT  /auth/me               → mettre à jour le profil
POST /auth/verify-email     → vérifier l'email
POST /auth/forgot-password  → demander un reset
POST /auth/reset-password   → réinitialiser le mot de passe
POST /auth/change-password  → changer le mot de passe (connecté)
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Rate limiting — récupère le limiter depuis app.state (configuré dans main.py)
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    _limiter = Limiter(key_func=get_remote_address)
except ImportError:
    _limiter = None

from backend.database import get_db
from backend.models import Abonne, PreferenceAlerte
from backend.schemas import RegisterIn, LoginIn, AbonneOut, AbonneUpdate
from backend.security import (
    hash_password, verify_password, validate_password_strength,
    create_access_token, create_refresh_token,
    verify_refresh_token, revoke_refresh_token,
    create_verification_token, verify_email_token,
    create_reset_token, verify_reset_token,
    check_login_attempts, record_failed_login, clear_login_attempts,
    get_current_abonne,
)

logger = logging.getLogger("netsync.auth")
router = APIRouter()


# ── Schemas spécifiques auth ───────────────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    abonne_id: str
    plan: str

class RefreshRequest(BaseModel):
    refresh_token: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class VerifyEmailRequest(BaseModel):
    token: str


# ── Register ───────────────────────────────────────────────────────────────────
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: Request,
    body: RegisterIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Créer un nouveau compte abonné."""
    # Valider la robustesse du mot de passe
    if not validate_password_strength(body.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe trop faible : 8 caractères minimum, 1 majuscule, 1 chiffre",
        )

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
        plan=body.plan if hasattr(body, 'plan') and body.plan else "gratuit",
        email_verifie=False,
        actif=True,
        ao_consultes_auj=0,
    )
    db.add(abonne)
    db.flush()

    # Créer préférences d'alertes par défaut
    if hasattr(body, 'secteurs') and body.secteurs:
        pref = PreferenceAlerte(
            abonne_id=abonne.id,
            secteurs=body.secteurs,
            canal_email=True,
            canal_whatsapp=False,
        )
        db.add(pref)

    db.commit()
    db.refresh(abonne)

    # Email de vérification en arrière-plan
    token = create_verification_token(str(abonne.id))
    background_tasks.add_task(_send_verification_email, abonne.email, token)
    logger.info(f"Inscription: {abonne.email} ({abonne.plan})")

    return TokenResponse(
        access_token=create_access_token(str(abonne.id)),
        refresh_token=create_refresh_token(str(abonne.id)),
        abonne_id=str(abonne.id),
        plan=abonne.plan,
    )


# ── Login ──────────────────────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
def login(request: Request, body: LoginIn, db: Session = Depends(get_db)):
    """Authentification — retourne access + refresh token."""
    # Vérifier le blocage après trop de tentatives
    if not check_login_attempts(body.email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de tentatives. Réessayez dans 15 minutes.",
        )

    abonne = db.query(Abonne).filter(Abonne.email == body.email).first()
    if not abonne or not abonne.password_hash:
        record_failed_login(body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    if not verify_password(body.password, abonne.password_hash):
        record_failed_login(body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    if not abonne.actif:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé — contactez le support",
        )

    # Login réussi : réinitialiser le compteur
    clear_login_attempts(body.email)

    return TokenResponse(
        access_token=create_access_token(str(abonne.id)),
        refresh_token=create_refresh_token(str(abonne.id)),
        abonne_id=str(abonne.id),
        plan=abonne.plan,
    )


# ── Refresh token ──────────────────────────────────────────────────────────────
@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    """Renouveler l'access token avec un refresh token valide."""
    abonne_id = verify_refresh_token(body.refresh_token)
    if not abonne_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide ou expiré",
        )

    abonne = db.get(Abonne, abonne_id)
    if not abonne or not abonne.actif:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Compte introuvable ou désactivé",
        )

    # Rotation : révoquer l'ancien, créer un nouveau
    revoke_refresh_token(body.refresh_token)

    return TokenResponse(
        access_token=create_access_token(str(abonne.id)),
        refresh_token=create_refresh_token(str(abonne.id)),
        abonne_id=str(abonne.id),
        plan=abonne.plan,
    )


# ── Logout ─────────────────────────────────────────────────────────────────────
@router.post("/logout")
def logout(body: RefreshRequest):
    """Révoquer le refresh token (déconnexion)."""
    revoke_refresh_token(body.refresh_token)
    return {"message": "Déconnexion réussie"}


# ── Me ─────────────────────────────────────────────────────────────────────────
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


# ── Change password (connecté) ─────────────────────────────────────────────────
@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current: Abonne = Depends(get_current_abonne),
):
    """Changer son mot de passe (nécessite le mot de passe actuel)."""
    if not verify_password(body.current_password, current.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect",
        )

    if not validate_password_strength(body.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nouveau mot de passe trop faible : 8 caractères, 1 majuscule, 1 chiffre",
        )

    current.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Mot de passe modifié avec succès"}


# ── Verify email ───────────────────────────────────────────────────────────────
@router.post("/verify-email")
def verify_email(body: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Valide l'email d'un abonné via le token envoyé par email."""
    abonne_id = verify_email_token(body.token)
    if not abonne_id:
        raise HTTPException(status_code=400, detail="Token invalide ou expiré")
    abonne = db.get(Abonne, abonne_id)
    if not abonne:
        raise HTTPException(status_code=404, detail="Abonné introuvable")
    abonne.email_verifie = True
    db.commit()
    return {"message": "Email vérifié avec succès"}


# ── Forgot password ────────────────────────────────────────────────────────────
@router.post("/forgot-password")
def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Envoie un email de réinitialisation du mot de passe."""
    abonne = db.query(Abonne).filter(Abonne.email == body.email).first()
    if abonne:
        token = create_reset_token(str(abonne.id))
        background_tasks.add_task(_send_reset_email, body.email, token)
    # Toujours 200 pour ne pas révéler si l'email existe
    return {"message": "Si cet email existe, un lien de réinitialisation a été envoyé"}


# ── Reset password ─────────────────────────────────────────────────────────────
@router.post("/reset-password")
def reset_password(request: Request, body: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Réinitialise le mot de passe via un token valide."""
    if not validate_password_strength(body.new_password):
        raise HTTPException(
            status_code=400,
            detail="Mot de passe trop faible : 8 caractères, 1 majuscule, 1 chiffre",
        )

    abonne_id = verify_reset_token(body.token)
    if not abonne_id:
        raise HTTPException(status_code=400, detail="Token invalide ou expiré")

    abonne = db.get(Abonne, abonne_id)
    if not abonne:
        raise HTTPException(status_code=404, detail="Abonné introuvable")

    abonne.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Mot de passe réinitialisé avec succès"}


# ── Email helpers (simulation en dev) ──────────────────────────────────────────
def _send_verification_email(email: str, token: str):
    verify_url = f"https://gov.netsync.bf/verify?token={token}"
    logger.info(f"[EMAIL] Vérification → {email} | {verify_url}")


def _send_reset_email(email: str, token: str):
    reset_url = f"https://gov.netsync.bf/reset-password?token={token}"
    logger.info(f"[EMAIL] Reset password → {email} | {reset_url}")
