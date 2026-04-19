"""
NetSync Gov — Gestionnaire webhook CinetPay (FastAPI)
Remplace et complète le endpoint /paiements/webhook de l'API.
"""
import logging
from typing import Optional

from fastapi import Request, HTTPException, Header
from sqlalchemy.orm import Session

from cinetpay_client import CinetPayClient
from subscription_service import SubscriptionService

logger = logging.getLogger("netsync.webhook")

cinetpay = CinetPayClient()


async def handle_cinetpay_webhook(
    request: Request,
    db: Session,
    x_cinetpay_signature: Optional[str] = Header(None),
) -> dict:
    """
    Handler principal du webhook CinetPay.

    Flux :
    1. Parser le corps (form-encoded ou JSON selon la config CinetPay)
    2. Vérifier la signature HMAC si disponible
    3. Déléguer à SubscriptionService.activate_from_webhook()
    4. Retourner 200 immédiatement (CinetPay ne retente que si erreur 5xx)

    Note : CinetPay retente le webhook jusqu'à 3 fois si le serveur répond
    autre chose que 200. L'idempotence est donc critique.
    """
    # ── Parser le corps ──────────────────────────────────────────────────────
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Corps JSON invalide")
    else:
        # CinetPay envoie parfois en application/x-www-form-urlencoded
        try:
            form_data = await request.form()
            body = dict(form_data)
        except Exception:
            raise HTTPException(status_code=400, detail="Corps form invalide")

    transaction_id = body.get("cpm_trans_id") or body.get("transaction_id")
    logger.info(f"Webhook CinetPay reçu : txn={transaction_id}")

    # ── Vérifier signature ───────────────────────────────────────────────────
    signature = x_cinetpay_signature or body.get("cpm_checksum")
    if signature:
        if not cinetpay.verify_webhook_signature(body, signature):
            logger.warning(f"Signature invalide — webhook rejeté txn={transaction_id}")
            # On retourne 200 quand même pour éviter les retries CinetPay
            # mais on ne traite pas le paiement
            return {"status": "signature_invalid", "processed": False}

    # ── Traiter le paiement ──────────────────────────────────────────────────
    service  = SubscriptionService(db)
    paiement = service.activate_from_webhook(body)

    if paiement is None:
        return {"status": "ignored", "transaction_id": transaction_id}

    return {
        "status":         "ok",
        "transaction_id": transaction_id,
        "paiement_statut": paiement.statut,
        "plan":           paiement.plan if paiement.statut == "success" else None,
    }
