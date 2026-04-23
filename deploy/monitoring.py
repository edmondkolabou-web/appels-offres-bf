"""
NetSync Gov — Script de monitoring
Vérifie l'état de tous les services et envoie des alertes.
Exécuter via cron toutes les 5 minutes.
"""
import os
import sys
import json
import logging
import requests
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("netsync.monitor")

API_URL = os.getenv("API_URL", "http://localhost:8000")
ALERT_WEBHOOK = os.getenv("MONITOR_WEBHOOK", "")

def check_api():
    try:
        r = requests.get(f"{API_URL}/health", timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {"service": "api", "status": "ok", "version": data.get("version")}
        return {"service": "api", "status": "error", "code": r.status_code}
    except Exception as e:
        return {"service": "api", "status": "down", "error": str(e)}

def check_db():
    try:
        r = requests.get(f"{API_URL}/health", timeout=10)
        return {"service": "database", "status": "ok" if r.status_code == 200 else "error"}
    except:
        return {"service": "database", "status": "down"}

def check_redis():
    try:
        import redis
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        r.ping()
        return {"service": "redis", "status": "ok"}
    except Exception as e:
        return {"service": "redis", "status": "down", "error": str(e)}

def check_disk():
    import shutil
    usage = shutil.disk_usage("/")
    pct = usage.used / usage.total * 100
    status = "ok" if pct < 85 else "warning" if pct < 95 else "critical"
    return {"service": "disk", "status": status, "usage_pct": round(pct, 1)}

def send_alert(checks):
    failures = [c for c in checks if c["status"] != "ok"]
    if not failures:
        return
    msg = f"⚠️ NetSync Gov — {len(failures)} service(s) en erreur:\n"
    for f in failures:
        msg += f"  • {f['service']}: {f['status']}\n"
    logger.warning(msg)
    if ALERT_WEBHOOK:
        try:
            requests.post(ALERT_WEBHOOK, json={"text": msg}, timeout=5)
        except:
            pass

if __name__ == "__main__":
    checks = [check_api(), check_db(), check_redis(), check_disk()]
    print(json.dumps({"timestamp": datetime.now().isoformat(), "checks": checks}, indent=2))
    send_alert(checks)
    if any(c["status"] == "down" for c in checks):
        sys.exit(1)
