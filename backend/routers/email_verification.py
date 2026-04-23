"""
NetSync Gov — Vérification email fonctionnelle via Resend
POST /auth/send-verification  → envoyer/renvoyer l'email de vérification
POST /auth/verify-email       → vérifier le token
"""
import os
import logging

import requests
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Abonne
from backend.security import (
    get_current_abonne, create_verification_token, verify_email_token
)

logger = logging.getLogger("netsync.email_verify")
router = APIRouter()

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM = os.getenv("RESEND_FROM_EMAIL", "alertes@gov.netsync.bf")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


class VerifyRequest(BaseModel):
    token: str


@router.post("/send-verification")
def send_verification_email(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current: Abonne = Depends(get_current_abonne),
):
    """Envoie ou renvoie l'email de vérification."""
    if current.email_verifie:
        return {"message": "Votre email est déjà vérifié"}

    token = create_verification_token(str(current.id))
    background_tasks.add_task(_send_verification, current.email, current.prenom, token)

    return {"message": f"Email de vérification envoyé à {current.email}"}


@router.post("/verify-email")
def verify_email(body: VerifyRequest, db: Session = Depends(get_db)):
    """Vérifie l'email avec le token reçu."""
    abonne_id = verify_email_token(body.token)
    if not abonne_id:
        raise HTTPException(status_code=400, detail="Token invalide ou expiré")

    abonne = db.get(Abonne, abonne_id)
    if not abonne:
        raise HTTPException(status_code=404, detail="Compte introuvable")

    abonne.email_verifie = True
    db.commit()

    return {"message": "Email vérifié avec succès", "email": abonne.email}


def _send_verification(email: str, prenom: str, token: str):
    """Envoie l'email de vérification via Resend API."""
    verify_url = f"{FRONTEND_URL}/verify?token={token}"

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
        <div style="background:#0082C9;padding:20px;border-radius:8px 8px 0 0;">
            <h1 style="color:white;margin:0;font-size:24px;">NetSync Gov</h1>
            <p style="color:rgba(255,255,255,0.8);margin:5px 0 0;">Appels d'Offres — Burkina Faso</p>
        </div>
        <div style="background:#f8f9fa;padding:30px;border:1px solid #dee2e6;border-top:none;">
            <h2 style="color:#0C1B2A;margin-top:0;">Bonjour {prenom or 'cher utilisateur'} !</h2>
            <p style="color:#333;line-height:1.6;">
                Merci de vous être inscrit sur NetSync Gov. Pour activer votre compte et recevoir
                vos alertes d'appels d'offres, veuillez confirmer votre adresse email.
            </p>
            <div style="text-align:center;margin:30px 0;">
                <a href="{verify_url}"
                   style="background:#0082C9;color:white;padding:12px 32px;border-radius:6px;
                          text-decoration:none;font-weight:bold;font-size:16px;">
                    Vérifier mon email
                </a>
            </div>
            <p style="color:#666;font-size:13px;">
                Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :<br>
                <a href="{verify_url}" style="color:#0082C9;word-break:break-all;">{verify_url}</a>
            </p>
            <p style="color:#999;font-size:12px;margin-top:30px;">
                Ce lien expire dans 24 heures. Si vous n'avez pas créé de compte,
                ignorez cet email.
            </p>
        </div>
        <div style="text-align:center;padding:15px;color:#999;font-size:11px;">
            NetSync Gov — Un produit NetSync Africa | Ouagadougou, Burkina Faso
        </div>
    </div>
    """

    if not RESEND_API_KEY:
        logger.info(f"[DEV] Email vérification → {email} | URL: {verify_url}")
        return

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": RESEND_FROM,
                "to": [email],
                "subject": "Vérifiez votre email — NetSync Gov",
                "html": html,
                "tags": [{"name": "type", "value": "verification"}],
            },
        )
        if resp.status_code in (200, 201):
            logger.info(f"Email vérification envoyé à {email}")
        else:
            logger.error(f"Resend erreur {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.error(f"Erreur envoi email: {e}")
