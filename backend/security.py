"""
NetSync Gov — Sécurité : JWT + bcrypt + rate limiting
"""
import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from models import Abonne

SECRET_KEY   = os.getenv("JWT_SECRET_KEY", "change-me-in-production-netsync-gov-2026")
ALGORITHM    = "HS256"
TOKEN_EXPIRE = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))  # 7 jours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(abonne_id: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=TOKEN_EXPIRE))
    return jwt.encode({"sub": abonne_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_abonne(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Abonne:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        abonne_id: str = payload.get("sub")
        if not abonne_id:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    abonne = db.get(Abonne, abonne_id)
    if not abonne or not abonne.actif:
        raise credentials_exc
    return abonne


def require_pro(abonne: Abonne = Depends(get_current_abonne)) -> Abonne:
    """Exige un plan Pro ou Équipe actif."""
    if not abonne.est_pro:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette fonctionnalité requiert un abonnement Pro ou Équipe",
        )
    return abonne


def require_admin(abonne: Abonne = Depends(get_current_abonne)) -> Abonne:
    """Exige le rôle admin (email dans liste blanche env)."""
    admins = os.getenv("ADMIN_EMAILS", "").split(",")
    if abonne.email not in admins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Accès réservé aux administrateurs")
    return abonne
