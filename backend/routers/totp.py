"""
NetSync Gov — Router : 2FA TOTP (Google Authenticator)
POST /auth/2fa/setup     → générer le secret + QR code
POST /auth/2fa/verify    → activer le 2FA avec un code valide
POST /auth/2fa/disable   → désactiver le 2FA
POST /auth/2fa/validate  → valider le code TOTP au login
"""
import io
import base64
import secrets
import logging

import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Abonne
from backend.security import get_current_abonne, verify_password

logger = logging.getLogger("netsync.2fa")
router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────
class TOTPSetupResponse(BaseModel):
    secret: str
    qr_code_base64: str
    otpauth_url: str
    backup_codes: list[str]

class TOTPCodeRequest(BaseModel):
    code: str

class TOTPDisableRequest(BaseModel):
    password: str
    code: str


# ── Setup 2FA ──────────────────────────────────────────────────────────────────
@router.post("/setup", response_model=TOTPSetupResponse)
def setup_2fa(
    db: Session = Depends(get_db),
    current: Abonne = Depends(get_current_abonne),
):
    """Génère un secret TOTP + QR code pour Google Authenticator."""
    if current.totp_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA est déjà activé sur ce compte",
        )

    # Générer le secret
    secret = pyotp.random_base32()
    current.totp_secret = secret
    db.commit()

    # Générer l'URL otpauth
    totp = pyotp.TOTP(secret)
    otpauth_url = totp.provisioning_uri(
        name=current.email,
        issuer_name="NetSync Gov"
    )

    # Générer le QR code en base64
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(otpauth_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    # Générer 8 codes de backup
    backup_codes = [secrets.token_hex(4).upper() for _ in range(8)]
    current.totp_backup_codes = ",".join(backup_codes)
    db.commit()

    logger.info(f"2FA setup initié pour {current.email}")

    return TOTPSetupResponse(
        secret=secret,
        qr_code_base64=qr_base64,
        otpauth_url=otpauth_url,
        backup_codes=backup_codes,
    )


# ── Verify & Activate 2FA ─────────────────────────────────────────────────────
@router.post("/verify")
def verify_2fa(
    body: TOTPCodeRequest,
    db: Session = Depends(get_db),
    current: Abonne = Depends(get_current_abonne),
):
    """Active le 2FA en vérifiant un code TOTP valide."""
    if current.totp_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA est déjà activé",
        )

    if not current.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lancez d'abord /auth/2fa/setup",
        )

    totp = pyotp.TOTP(current.totp_secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code TOTP invalide. Vérifiez votre application Google Authenticator.",
        )

    current.totp_active = True
    db.commit()

    logger.info(f"2FA activé pour {current.email}")
    return {"message": "2FA activé avec succès. Conservez vos codes de backup."}


# ── Validate TOTP at login ─────────────────────────────────────────────────────
@router.post("/validate")
def validate_2fa(
    body: TOTPCodeRequest,
    db: Session = Depends(get_db),
    current: Abonne = Depends(get_current_abonne),
):
    """Valide un code TOTP lors de la connexion."""
    if not current.totp_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA n'est pas activé sur ce compte",
        )

    totp = pyotp.TOTP(current.totp_secret)

    # Vérifier le code TOTP
    if totp.verify(body.code, valid_window=1):
        return {"message": "Code 2FA valide", "valid": True}

    # Vérifier les codes de backup
    if current.totp_backup_codes:
        backup_list = current.totp_backup_codes.split(",")
        if body.code.upper() in backup_list:
            backup_list.remove(body.code.upper())
            current.totp_backup_codes = ",".join(backup_list)
            db.commit()
            logger.info(f"Code backup utilisé par {current.email}, {len(backup_list)} restants")
            return {"message": "Code backup accepté", "valid": True, "backup_remaining": len(backup_list)}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Code 2FA invalide",
    )


# ── Disable 2FA ────────────────────────────────────────────────────────────────
@router.post("/disable")
def disable_2fa(
    body: TOTPDisableRequest,
    db: Session = Depends(get_db),
    current: Abonne = Depends(get_current_abonne),
):
    """Désactive le 2FA (nécessite mot de passe + code TOTP)."""
    if not current.totp_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA n'est pas activé",
        )

    # Vérifier le mot de passe
    if not verify_password(body.password, current.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe incorrect",
        )

    # Vérifier le code TOTP
    totp = pyotp.TOTP(current.totp_secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code TOTP invalide",
        )

    current.totp_secret = None
    current.totp_active = False
    current.totp_backup_codes = None
    db.commit()

    logger.info(f"2FA désactivé pour {current.email}")
    return {"message": "2FA désactivé avec succès"}
