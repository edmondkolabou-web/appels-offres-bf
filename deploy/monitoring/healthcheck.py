"""
NetSync Gov — Script de monitoring santé
Vérifie tous les composants et envoie une alerte si anomalie.
Usage : python healthcheck.py  (ou via cron toutes les 5 min)
"""
import os
import sys
import logging
import requests
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("netsync.health")

API_URL     = os.getenv("API_URL", "https://api.gov.netsync.bf")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@netsync.bf")
TIMEOUT     = 10


def check_api() -> dict:
    try:
        r = requests.get(f"{API_URL}/health", timeout=TIMEOUT)
        ok = r.status_code == 200 and r.json().get("status") == "ok"
        return {"name": "API FastAPI", "ok": ok, "detail": r.json() if ok else r.text}
    except Exception as e:
        return {"name": "API FastAPI", "ok": False, "detail": str(e)}


def check_db(db_url: str) -> dict:
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(db_url, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM appels_offres")).scalar()
        return {"name": "PostgreSQL", "ok": True, "detail": f"{result} AOs en base"}
    except Exception as e:
        return {"name": "PostgreSQL", "ok": False, "detail": str(e)}


def check_redis(redis_url: str) -> dict:
    try:
        import redis
        r = redis.from_url(redis_url, socket_timeout=5)
        r.ping()
        return {"name": "Redis", "ok": True, "detail": "PONG"}
    except Exception as e:
        return {"name": "Redis", "ok": False, "detail": str(e)}


def check_pipeline_recent(db_url: str) -> dict:
    """Vérifie que le pipeline a tourné dans les dernières 26h (marge 2h)."""
    try:
        from sqlalchemy import create_engine, text
        from datetime import timedelta
        engine = create_engine(db_url)
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT run_at, statut FROM pipeline_logs "
                "ORDER BY run_at DESC LIMIT 1"
            )).fetchone()
        if not row:
            return {"name": "Pipeline PDF", "ok": False, "detail": "Aucun log pipeline"}
        age = datetime.utcnow() - row.run_at.replace(tzinfo=None)
        ok  = age.total_seconds() < 26 * 3600
        return {
            "name":   "Pipeline PDF",
            "ok":     ok,
            "detail": f"Dernier run : {row.run_at.strftime('%d/%m %H:%M')} ({row.statut})"
        }
    except Exception as e:
        return {"name": "Pipeline PDF", "ok": False, "detail": str(e)}


def check_ssl(domain: str) -> dict:
    """Vérifie que le certificat SSL expire dans plus de 14 jours."""
    import ssl
    import socket
    from datetime import timezone
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                expiry_str = cert["notAfter"]
                expiry = datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z")
                days_left = (expiry - datetime.utcnow()).days
                ok = days_left > 14
                return {
                    "name":   "SSL Certificate",
                    "ok":     ok,
                    "detail": f"Expire dans {days_left} jours ({expiry.strftime('%d/%m/%Y')})"
                }
    except Exception as e:
        return {"name": "SSL Certificate", "ok": False, "detail": str(e)}


def send_alert(message: str) -> None:
    """Envoie une alerte email admin si anomalie détectée."""
    resend_key = os.getenv("RESEND_API_KEY", "")
    if not resend_key:
        logger.warning(f"[ALERTE NON ENVOYÉE] {message}")
        return
    try:
        requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {resend_key}"},
            json={
                "from": "monitoring@gov.netsync.bf",
                "to": [ADMIN_EMAIL],
                "subject": "[NetSync Gov] ⚠️ Anomalie détectée",
                "html": f"<p><strong>Anomalie détectée :</strong></p><pre>{message}</pre>"
                        f"<p>Heure : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>",
            },
            timeout=10,
        )
    except Exception as e:
        logger.error(f"Envoi alerte monitoring échoué : {e}")


def run_checks() -> bool:
    """Exécute tous les checks et retourne False si anomalie."""
    db_url    = os.getenv("DATABASE_URL", "")
    redis_url = os.getenv("REDIS_URL", "")
    domain    = os.getenv("DOMAIN", "gov.netsync.bf")

    checks = [check_api()]
    if db_url:
        checks += [check_db(db_url), check_pipeline_recent(db_url)]
    if redis_url:
        checks.append(check_redis(redis_url))
    checks.append(check_ssl(domain))

    all_ok  = True
    failures = []

    for check in checks:
        status = "OK" if check["ok"] else "FAIL"
        logger.info(f"[{status}] {check['name']} — {check['detail']}")
        if not check["ok"]:
            all_ok = False
            failures.append(f"❌ {check['name']}: {check['detail']}")

    if failures:
        send_alert("\n".join(failures))

    return all_ok


if __name__ == "__main__":
    ok = run_checks()
    sys.exit(0 if ok else 1)
