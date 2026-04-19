"""
NetSync Gov — API FastAPI principale
Endpoints : AOs, Auth, Alertes, Favoris, Paiements, Admin
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from backend.routers import aos, auth, alertes, favoris, paiements, admin

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s")
logger = logging.getLogger("netsync.api")

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="NetSync Gov API",
    description="Agrégateur Appels d'Offres Burkina Faso — API REST",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://gov.netsync.bf", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth.router,      prefix="/api/v1/auth",      tags=["Auth"])
app.include_router(aos.router,       prefix="/api/v1/aos",        tags=["Appels d'offres"])
app.include_router(alertes.router,   prefix="/api/v1/alertes",    tags=["Alertes"])
app.include_router(favoris.router,   prefix="/api/v1/favoris",    tags=["Favoris"])
app.include_router(paiements.router, prefix="/api/v1/paiements",  tags=["Paiements"])
app.include_router(admin.router,     prefix="/api/v1/admin",      tags=["Admin"])

# ── Healthcheck ────────────────────────────────────────────────────────────────
@app.get("/health", tags=["Monitoring"])
def health():
    return {"status": "ok", "service": "netsync-gov-api", "version": "1.0.0"}

# ── Handler erreurs global ─────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erreur non gérée : {exc}", exc_info=True)
    return JSONResponse(status_code=500,
                        content={"detail": "Erreur interne du serveur"})
