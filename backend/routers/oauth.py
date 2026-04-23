"""
NetSync Gov — Router : OAuth2 Social Login (Google)
GET  /auth/oauth/google        → rediriger vers Google
GET  /auth/oauth/google/callback → callback après consentement
"""
import os
import logging
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Abonne
from backend.security import (
    create_access_token, create_refresh_token, hash_password
)

logger = logging.getLogger("netsync.oauth")
router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/auth/oauth/google/callback")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/google")
def google_login():
    """Redirige l'utilisateur vers la page de consentement Google."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth non configuré. Ajoutez GOOGLE_CLIENT_ID dans .env")

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return {"auth_url": auth_url}


@router.get("/google/callback")
def google_callback(
    code: str = Query(...),
    db: Session = Depends(get_db),
):
    """Callback Google OAuth2. Échange le code contre un token et crée/connecte l'utilisateur."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Google OAuth non configuré")

    # Échanger le code contre un access token Google
    token_data = requests.post(GOOGLE_TOKEN_URL, data={
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }).json()

    if "access_token" not in token_data:
        logger.error(f"Google OAuth erreur: {token_data}")
        raise HTTPException(status_code=400, detail="Erreur d'authentification Google")

    # Récupérer les infos utilisateur
    userinfo = requests.get(GOOGLE_USERINFO_URL, headers={
        "Authorization": f"Bearer {token_data['access_token']}"
    }).json()

    email = userinfo.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email non fourni par Google")

    # Chercher ou créer l'utilisateur
    abonne = db.query(Abonne).filter(Abonne.email == email).first()

    if not abonne:
        # Créer un nouveau compte
        abonne = Abonne(
            email=email,
            password_hash=hash_password(os.urandom(32).hex()),
            prenom=userinfo.get("given_name", ""),
            nom=userinfo.get("family_name", ""),
            plan="gratuit",
            email_verifie=True,
            actif=True,
            ao_consultes_auj=0,
        )
        db.add(abonne)
        db.commit()
        db.refresh(abonne)
        logger.info(f"Nouveau compte OAuth Google: {email}")
    else:
        # Marquer l'email comme vérifié (Google l'a vérifié)
        if not abonne.email_verifie:
            abonne.email_verifie = True
            db.commit()

    # Générer les tokens NetSync Gov
    access_token = create_access_token(str(abonne.id))
    refresh_token = create_refresh_token(str(abonne.id))

    # Rediriger vers le frontend avec les tokens
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    redirect_url = f"{frontend_url}/auth?access_token={access_token}&refresh_token={refresh_token}&plan={abonne.plan}"

    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=redirect_url)
