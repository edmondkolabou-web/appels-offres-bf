"""
NetSync Gov — Module envoi email via Resend
Gestion des envois, retry, tracking, logs.
"""
import os
import logging
from typing import Optional

import requests

logger = logging.getLogger("netsync.email")

RESEND_API_KEY   = os.getenv("RESEND_API_KEY", "")
RESEND_FROM      = os.getenv("RESEND_FROM_EMAIL", "alertes@gov.netsync.bf")
RESEND_REPLY_TO  = os.getenv("RESEND_REPLY_TO", "support@netsync.bf")
RESEND_API_URL   = "https://api.resend.com/emails"

MAX_RETRIES = 2


class ResendClient:
    """Envoi d'emails transactionnels via l'API Resend."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        })

    def send(self, to: str, subject: str, html: str,
             tags: Optional[list] = None) -> dict:
        """
        Envoie un email HTML via Resend.

        Args:
            to: Adresse email destinataire
            subject: Objet du message
            html: Corps HTML de l'email
            tags: Tags Resend pour le suivi (ex: [{"name": "type", "value": "alerte_ao"}])

        Returns:
            dict avec 'success', 'email_id' ou 'error'
        """
        if not RESEND_API_KEY:
            # Mode simulation
            logger.info(f"[SIMULATION EMAIL] → {to} | {subject}")
            return {"success": True, "simulated": True, "email_id": "sim_0"}

        payload = {
            "from": RESEND_FROM,
            "to": [to],
            "subject": subject,
            "html": html,
            "reply_to": RESEND_REPLY_TO,
        }
        if tags:
            payload["tags"] = tags

        for attempt in range(1, MAX_RETRIES + 2):
            try:
                resp = self.session.post(RESEND_API_URL, json=payload, timeout=15)
                data = resp.json()

                if resp.status_code in (200, 201):
                    email_id = data.get("id", "")
                    logger.info(f"Email envoyé → {to} | id={email_id}")
                    return {"success": True, "email_id": email_id}

                # 429 = rate limit — attendre et retry
                if resp.status_code == 429 and attempt <= MAX_RETRIES:
                    import time
                    retry_after = int(resp.headers.get("Retry-After", 10))
                    logger.warning(f"Rate limit Resend, retry dans {retry_after}s (tentative {attempt})")
                    time.sleep(retry_after)
                    continue

                # Erreur permanente
                err = data.get("message", "Erreur inconnue")
                logger.error(f"Resend erreur {resp.status_code} → {to}: {err}")
                return {"success": False, "error": err, "status_code": resp.status_code}

            except requests.Timeout:
                logger.error(f"Resend timeout (tentative {attempt}) → {to}")
                if attempt > MAX_RETRIES:
                    return {"success": False, "error": "Timeout API Resend"}
            except requests.RequestException as e:
                logger.error(f"Resend exception → {to}: {e}")
                return {"success": False, "error": str(e)}

        return {"success": False, "error": "Max retries atteint"}

    def send_batch(self, emails: list[dict]) -> list[dict]:
        """
        Envoie plusieurs emails en série (Resend ne supporte pas le batch natif).
        Chaque dict doit avoir : to, subject, html, [tags].
        """
        results = []
        for email in emails:
            result = self.send(
                to=email["to"],
                subject=email["subject"],
                html=email["html"],
                tags=email.get("tags"),
            )
            result["to"] = email["to"]
            results.append(result)
        return results
