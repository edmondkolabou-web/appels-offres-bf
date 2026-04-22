"""
NetSync Gov — Sécurité complète SaaS
- JWT access token (15 min) + refresh token (7 jours)
- Tokens stockés en Redis (avec fallback mémoire en dev)
- Rate limiting (slowapi)
- Bcrypt password hashing
- Guards : get_current_abonne, require_pro, require_admin
"""
import os
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Abonne
from backend.config import config

logger = logging.getLogger("netsync.security")

# ── Configuration JWT ──────────────────────────────────────────────────────────
SECRET_KEY = config.JWT_SECRET_KEY
ALGORITHM = config.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE = 15          # minutes
REFRESH_TOKEN_EXPIRE = 60 * 24 * 7  # 7 jours en minutes

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── Redis token store (avec fallback dict en dev) ──────────────────────────────
class TokenStore:
    """Stocke les tokens de vérification et refresh tokens.
    Utilise Redis en production, dict en mémoire en dev."""

    def __init__(self):
        self._memory_store = {}
        self._redis = None
        self._init_redis()

    def _init_redis(self):
        try:
            import redis
            self._redis = redis.from_url(config.REDIS_URL, decode_responses=True)
            self._redis.ping()
            logger.info("TokenStore: Redis connecté")
        except Exception as e:
            logger.warning(f"TokenStore: Redis indisponible ({e}), fallback mémoire")
            self._redis = None

    def set(self, key: str, value: str, ttl_seconds: int = 3600):
        """Stocker un token avec TTL."""
        if self._redis:
            self._redis.setex(f"netsync:token:{key}", ttl_seconds, value)
        else:
            self._memory_store[key] = {
                "value": value,
                "expires": datetime.utcnow() + timedelta(seconds=ttl_seconds)
            }

    def get(self, key: str) -> Optional[str]:
        """Récupérer un token."""
        if self._redis:
            return self._redis.get(f"netsync:token:{key}")
        else:
            entry = self._memory_store.get(key)
            if entry and entry["expires"] > datetime.utcnow():
                return entry["value"]
            elif entry:
                del self._memory_store[key]
            return None

    def delete(self, key: str):
        """Supprimer un token."""
        if self._redis:
            self._redis.delete(f"netsync:token:{key}")
        else:
            self._memory_store.pop(key, None)

    def exists(self, key: str) -> bool:
        """Vérifier si un token existe."""
        return self.get(key) is not None


# Instance globale
token_store = TokenStore()


# ── Password hashing ──────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def validate_password_strength(password: str) -> bool:
    """Vérifie la robustesse du mot de passe : 8+ chars, 1 majuscule, 1 chiffre."""
    if len(password) < 8:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    return True


# ── JWT Tokens ─────────────────────────────────────────────────────────────────
def create_access_token(abonne_id: str) -> str:
    """Créer un access token court (15 min)."""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE)
    return jwt.encode(
        {"sub": str(abonne_id), "exp": expire, "type": "access"},
        SECRET_KEY, algorithm=ALGORITHM
    )


def create_refresh_token(abonne_id: str) -> str:
    """Créer un refresh token long (7 jours), stocké en Redis."""
    token = secrets.token_urlsafe(64)
    token_store.set(
        f"refresh:{token}",
        str(abonne_id),
        ttl_seconds=REFRESH_TOKEN_EXPIRE * 60
    )
    return token


def verify_refresh_token(refresh_token: str) -> Optional[str]:
    """Vérifie un refresh token et retourne l'abonne_id."""
    abonne_id = token_store.get(f"refresh:{refresh_token}")
    return abonne_id


def revoke_refresh_token(refresh_token: str):
    """Révoque un refresh token (logout)."""
    token_store.delete(f"refresh:{refresh_token}")


def create_verification_token(abonne_id: str) -> str:
    """Créer un token de vérification email (24h)."""
    token = secrets.token_urlsafe(32)
    token_store.set(f"verify:{token}", str(abonne_id), ttl_seconds=86400)
    return token


def verify_email_token(token: str) -> Optional[str]:
    """Vérifie un token d'email et retourne l'abonne_id."""
    abonne_id = token_store.get(f"verify:{token}")
    if abonne_id:
        token_store.delete(f"verify:{token}")
    return abonne_id


def create_reset_token(abonne_id: str) -> str:
    """Créer un token de reset password (1h)."""
    token = secrets.token_urlsafe(32)
    token_store.set(f"reset:{token}", str(abonne_id), ttl_seconds=3600)
    return token


def verify_reset_token(token: str) -> Optional[str]:
    """Vérifie un token de reset et retourne l'abonne_id."""
    abonne_id = token_store.get(f"reset:{token}")
    if abonne_id:
        token_store.delete(f"reset:{token}")
    return abonne_id


# ── Login attempt tracking ─────────────────────────────────────────────────────
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 900  # 15 minutes


def check_login_attempts(email: str) -> bool:
    """Vérifie si le compte est verrouillé après trop de tentatives."""
    attempts = token_store.get(f"login_attempts:{email}")
    if attempts and int(attempts) >= MAX_LOGIN_ATTEMPTS:
        return False
    return True


def record_failed_login(email: str):
    """Enregistre une tentative de connexion échouée."""
    key = f"login_attempts:{email}"
    current = token_store.get(key)
    count = int(current) + 1 if current else 1
    token_store.set(key, str(count), ttl_seconds=LOGIN_LOCKOUT_SECONDS)


def clear_login_attempts(email: str):
    """Réinitialise le compteur après un login réussi."""
    token_store.delete(f"login_attempts:{email}")


# ── FastAPI Dependencies ───────────────────────────────────────────────────────
def get_current_abonne(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Abonne:
    """Extrait l'abonné depuis le JWT access token."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        abonne_id: str = payload.get("sub")
        token_type: str = payload.get("type", "access")
        if not abonne_id or token_type != "access":
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
    """Exige le rôle admin."""
    admins = config.ADMIN_EMAIL.split(",") if config.ADMIN_EMAIL else []
    if abonne.email not in admins:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs",
        )
    return abonne
