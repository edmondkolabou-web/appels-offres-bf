import os
import secrets
from pydantic_settings import BaseSettings

def _get_jwt_secret():
    """Retourne le JWT secret. En prod, DOIT être configuré via .env."""
    secret = os.getenv("JWT_SECRET_KEY", "")
    env = os.getenv("ENVIRONMENT", "development")
    if not secret and env == "production":
        raise RuntimeError(
            "ERREUR CRITIQUE : JWT_SECRET_KEY non configuré en production. "
            "Ajoutez JWT_SECRET_KEY dans votre .env avec une clé aléatoire de 64+ caractères. "
            "Générez-en une avec : python3 -c \"import secrets; print(secrets.token_hex(64))\""
        )
    return secret or f"dev-only-{secrets.token_hex(32)}"

class Config(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://netsync:devpassword@localhost:5432/netsync_gov_dev")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    JWT_SECRET_KEY: str = _get_jwt_secret()
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    RESEND_FROM_EMAIL: str = os.getenv("RESEND_FROM_EMAIL", "alertes@gov.netsync.bf")
    WHATSAPP_API_TOKEN: str = os.getenv("WHATSAPP_API_TOKEN", "")
    WHATSAPP_PHONE_ID: str = os.getenv("WHATSAPP_PHONE_ID", "")
    WHATSAPP_WABA_ID: str = os.getenv("WHATSAPP_WABA_ID", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CINETPAY_SITE_ID: str = os.getenv("CINETPAY_SITE_ID", "")
    CINETPAY_API_KEY: str = os.getenv("CINETPAY_API_KEY", "")
    CINETPAY_SECRET_KEY: str = os.getenv("CINETPAY_SECRET_KEY", "")
    CINETPAY_NOTIFY_URL: str = os.getenv("CINETPAY_NOTIFY_URL", "")
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "")

    class Config:
        env_file = ".env.dev"
        extra = "ignore"

config = Config()
