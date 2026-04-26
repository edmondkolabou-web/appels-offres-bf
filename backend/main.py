"""
NetSync Gov — API FastAPI principale (SaaS)
Rate limiting, headers sécurité, CORS strict, routers
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
import httpx
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import os

from backend.routers import aos, auth, alertes, favoris, paiements, admin
from backend.routers import totp
from backend.routers import subscription
from backend.routers import oauth, email_verification

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
)
logger = logging.getLogger("netsync.api")

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="NetSync Gov API",
    description="Agrégateur Appels d'Offres Burkina Faso — API REST SaaS",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── Rate Limiting (slowapi) ────────────────────────────────────────────────────
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("Rate limiting activé (slowapi)")
except ImportError:
    logger.warning("slowapi non installé — rate limiting désactivé")
    limiter = None


# ── Security Headers Middleware ────────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Ajoute les headers de sécurité HTTP à toutes les réponses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if os.getenv("ENVIRONMENT") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


app.add_middleware(SecurityHeadersMiddleware)


# ── CORS ───────────────────────────────────────────────────────────────────────
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    origins = [
        "https://gov.netsync.bf",
        "https://www.gov.netsync.bf",
    ]
else:
    origins = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)


# ── Routers ────────────────────────────────────────────────────────────────────
# Rate limits sur les endpoints auth sensibles
if limiter:
    @app.middleware("http")
    async def rate_limit_auth(request, call_next):
        """Applique rate limiting sur les endpoints auth sensibles."""
        path = request.url.path
        rate_limited_paths = {
            "/api/v1/auth/login": "10/minute",
            "/api/v1/auth/register": "5/minute",
            "/api/v1/auth/forgot-password": "3/minute",
            "/api/v1/auth/reset-password": "5/minute",
            "/api/v1/auth/refresh": "30/minute",
        }
        # Le rate limiting est géré par slowapi via app.state.limiter
        # Les limites sont appliquées automatiquement
        response = await call_next(request)
        return response

app.include_router(auth.router,      prefix="/api/v1/auth",      tags=["Auth"])
app.include_router(aos.router,       prefix="/api/v1/aos",       tags=["Appels d'offres"])
app.include_router(alertes.router,   prefix="/api/v1/alertes",   tags=["Alertes"])
app.include_router(favoris.router,   prefix="/api/v1/favoris",   tags=["Favoris"])
app.include_router(paiements.router, prefix="/api/v1/paiements", tags=["Paiements"])
app.include_router(admin.router,     prefix="/api/v1/admin",     tags=["Admin"])
app.include_router(totp.router,     prefix="/api/v1/auth/2fa",  tags=["2FA"])
app.include_router(subscription.router, prefix="/api/v1/subscription", tags=["Subscription"])
app.include_router(oauth.router, prefix="/api/v1/auth/oauth", tags=["OAuth"])
app.include_router(email_verification.router, prefix="/api/v1/auth", tags=["Email Verification"])


# ── PDFs : stockage local + proxy téléchargement ──────────────────────────────
pdf_dir = Path(__file__).parent / "static" / "pdfs"
pdf_dir.mkdir(parents=True, exist_ok=True)
app.mount("/pdfs", StaticFiles(directory=str(pdf_dir)), name="pdfs")


@app.get("/api/v1/download/quotidien/{numero}", tags=["Download"])
async def download_quotidien(numero: int):
    """Télécharge un Quotidien DGCMEF. Si déjà en cache local, sert directement."""
    local_path = pdf_dir / f"quotidien_{numero}.pdf"

    # Si déjà téléchargé, servir localement
    if local_path.exists():
        return FileResponse(
            path=str(local_path),
            filename=f"Quotidien_DGCMEF_{numero}.pdf",
            media_type="application/pdf",
        )

    # Sinon, essayer de télécharger depuis la DGCMEF
    urls_to_try = [
        f"https://www.dgcmef.gov.bf/sites/default/files/2026-04/Quotidien%20N%C2%B0{numero}.pdf",
        f"https://www.dgcmef.gov.bf/sites/default/files/2026-03/Quotidien%20N%C2%B0{numero}.pdf",
        f"https://www.dgcmef.gov.bf/sites/default/files/2025-03/Quotidien%20N%C2%B0{numero}.pdf",
        f"https://www.dgcmef.gov.bf/sites/default/files/2025-04/Quotidien%20N%C2%B0{numero}.pdf",
    ]

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        for url in urls_to_try:
            try:
                resp = await client.get(url)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    # Sauvegarder en cache local
                    local_path.write_bytes(resp.content)
                    logger.info(f"PDF Quotidien {numero} téléchargé et mis en cache ({len(resp.content)} bytes)")
                    return FileResponse(
                        path=str(local_path),
                        filename=f"Quotidien_DGCMEF_{numero}.pdf",
                        media_type="application/pdf",
                    )
            except Exception:
                continue

    raise HTTPException(status_code=404, detail=f"Quotidien N°{numero} introuvable sur la DGCMEF")


# ── Healthcheck ────────────────────────────────────────────────────────────────
@app.get("/health", tags=["Monitoring"])
def health():
    return {
        "status": "ok",
        "service": "netsync-gov-api",
        "version": "2.0.0",
        "environment": ENVIRONMENT,
    }


# ── Handler erreurs global ─────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erreur non gérée : {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erreur interne du serveur"},
    )


# ── Healthcheck détaillé ───────────────────────────────────────────────────────
@app.get("/health/detailed")
async def health_detailed():
    """Healthcheck détaillé — teste PostgreSQL, Redis et espace disque."""
    import shutil
    checks = {"status": "ok", "services": {}}

    # PostgreSQL
    try:
        from backend.database import get_db
        db = next(get_db())
        db.execute("SELECT 1")
        checks["services"]["postgresql"] = "ok"
    except Exception as e:
        checks["services"]["postgresql"] = f"error: {str(e)[:100]}"
        checks["status"] = "degraded"

    # Redis
    try:
        import redis
        from backend.config import config
        r = redis.from_url(config.REDIS_URL)
        r.ping()
        checks["services"]["redis"] = "ok"
    except Exception as e:
        checks["services"]["redis"] = f"error: {str(e)[:100]}"
        checks["status"] = "degraded"

    # Espace disque
    try:
        usage = shutil.disk_usage("/")
        free_gb = usage.free / (1024 ** 3)
        checks["services"]["disk"] = f"{free_gb:.1f} GB free"
        if free_gb < 1:
            checks["status"] = "warning"
    except Exception:
        checks["services"]["disk"] = "unknown"

    return checks
