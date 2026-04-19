import os
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://netsync:devpassword@localhost:5432/netsync_gov_dev")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-secret-key")
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
