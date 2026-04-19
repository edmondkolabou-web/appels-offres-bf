"""
NetSync Gov — Configuration pipeline PDF DGCMEF
"""
import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class Config:
    # ── DGCMEF ──
    DGCMEF_BASE_URL: str = "https://www.dgcmef.gov.bf"
    DGCMEF_INDEX_URL: str = "https://www.dgcmef.gov.bf/fr/appels-d-offre"
    DGCMEF_PDF_PATTERN: str = r"Quotidien[_\s-]*N[°o]?\s*(\d+)"

    # ── Sources secondaires ──
    CCI_BF_URL: str = "https://www.cci.bf/?q=fr/services-aux-usagers/opportunites-d-affaires/appel-d-offre"
    UNDP_RSS_URL: str = "https://procurement-notices.undp.org/view_negotiation.cfm?bid_ref=&country=BF"

    # ── Stockage ──
    PDF_STORAGE_DIR: str = os.getenv("PDF_STORAGE_DIR", "/data/pdfs")
    LOG_DIR: str = os.getenv("LOG_DIR", "/data/logs")

    # ── Base de données ──
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://netsync:pass@localhost:5432/netsync_gov")

    # ── Redis / Celery ──
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # ── Alertes ──
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    RESEND_FROM_EMAIL: str = os.getenv("RESEND_FROM_EMAIL", "alertes@gov.netsync.bf")
    WHATSAPP_API_TOKEN: str = os.getenv("WHATSAPP_API_TOKEN", "")
    WHATSAPP_PHONE_ID: str = os.getenv("WHATSAPP_PHONE_ID", "")

    # ── Pipeline ──
    CRON_SCHEDULE: str = "0 7 * * 1-5"   # Lun-Ven à 7h00
    RETRY_MAX: int = 3
    RETRY_DELAY_SEC: int = 300            # 5 min entre retries
    REQUEST_TIMEOUT: int = 30
    REQUEST_HEADERS: dict = field(default_factory=lambda: {
        "User-Agent": "NetSyncGov/1.0 (aggregateur AO Burkina Faso; contact@netsync.bf)",
        "Accept-Language": "fr-BF,fr;q=0.9",
    })

    # ── Parsing ──
    SECTEURS: List[str] = field(default_factory=lambda: [
        "informatique", "btp", "sante", "agriculture",
        "conseil", "equipement", "transport", "energie",
        "education", "hydraulique", "securite", "autre",
    ])
    TYPES_PROCEDURE: List[str] = field(default_factory=lambda: [
        "ouvert", "restreint", "dpx", "ami", "rfp", "rfq",
    ])
    MONTANT_SEUIL_FCFA: int = 15_000_000  # Seuil AO ouvert obligatoire

    # ── Claude API (fallback parsing) ──
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    CLAUDE_MAX_TOKENS: int = 1000
    USE_LLM_FALLBACK: bool = True

    # ── Monitoring ──
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@netsync.bf")


config = Config()
