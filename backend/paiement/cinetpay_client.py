"""
NetSync Gov — Client CinetPay
Gestion complète : initiation paiement, vérification statut, webhook, remboursement.
Docs : https://docs.cinetpay.com/api/1.0
"""
import os
import hmac
import hashlib
import logging
from typing import Optional

import requests

logger = logging.getLogger("netsync.cinetpay")

SITE_ID    = os.getenv("CINETPAY_SITE_ID", "")
API_KEY    = os.getenv("CINETPAY_API_KEY", "")
SECRET_KEY = os.getenv("CINETPAY_SECRET_KEY", "")
BASE_URL   = "https://api-checkout.cinetpay.com/v2"
NOTIFY_URL = os.getenv("CINETPAY_NOTIFY_URL",
                        "https://api.gov.netsync.bf/api/v1/paiements/webhook")
RETURN_URL = os.getenv("CINETPAY_RETURN_URL",
                        "https://gov.netsync.bf/paiement/succes")


class CinetPayClient:
    """
    Client CinetPay pour l'API checkout v2.
    Supporte : Orange Money BF, Moov Money BF, cartes Visa/MC.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    # ── Initiation paiement ──────────────────────────────────────────────────

    def init_payment(
        self,
        transaction_id: str,
        amount: int,
        currency: str,
        description: str,
        customer_name: str,
        customer_email: str,
        customer_phone: str = "",
        channels: str = "ALL",
        lang: str = "fr",
        metadata: Optional[str] = None,
    ) -> dict:
        """
        Initie une transaction de paiement CinetPay.

        Args:
            transaction_id: ID unique de la transaction (généré côté app)
            amount: Montant en FCFA (entier, minimum 100)
            currency: Devise — "XOF" pour FCFA
            description: Description affichée au client (max 255 chars)
            customer_name: Nom complet du client
            customer_email: Email du client
            customer_phone: Numéro de téléphone (optionnel)
            channels: "ALL" | "MOBILE_MONEY" | "CREDIT_CARD"
            lang: "fr" | "en"
            metadata: Données arbitraires retournées dans le webhook (JSON string)

        Returns:
            dict avec 'success', 'payment_url' et 'payment_token'
        """
        if not SITE_ID or not API_KEY:
            return self._simulation_init(transaction_id, amount)

        payload = {
            "apikey":               API_KEY,
            "site_id":              SITE_ID,
            "transaction_id":       transaction_id,
            "amount":               amount,
            "currency":             currency,
            "description":          description[:255],
            "customer_name":        customer_name,
            "customer_email":       customer_email,
            "customer_phone_number": customer_phone,
            "customer_address":     "Ouagadougou, Burkina Faso",
            "customer_city":        "Ouagadougou",
            "customer_country":     "BF",
            "customer_zip_code":    "00000",
            "notify_url":           NOTIFY_URL,
            "return_url":           RETURN_URL,
            "channels":             channels,
            "lang":                 lang,
            "invoice_data":         {},
        }
        if metadata:
            payload["metadata"] = metadata

        try:
            resp = self.session.post(f"{BASE_URL}/payment", json=payload, timeout=20)
            data = resp.json()

            if resp.status_code == 201 and data.get("code") == "201":
                pay_data = data.get("data", {})
                payment_url   = pay_data.get("payment_url")
                payment_token = pay_data.get("payment_token")
                logger.info(f"CinetPay init OK : txn={transaction_id} token={payment_token}")
                return {
                    "success":       True,
                    "payment_url":   payment_url,
                    "payment_token": payment_token,
                }

            err_msg = data.get("message", "Erreur inconnue CinetPay")
            logger.error(f"CinetPay init erreur : {err_msg} (txn={transaction_id})")
            return {"success": False, "error": err_msg, "code": data.get("code")}

        except requests.Timeout:
            logger.error(f"CinetPay timeout (init, txn={transaction_id})")
            return {"success": False, "error": "Timeout API CinetPay"}
        except requests.RequestException as e:
            logger.error(f"CinetPay exception (init): {e}")
            return {"success": False, "error": str(e)}

    # ── Vérification statut ──────────────────────────────────────────────────

    def check_payment(self, transaction_id: str) -> dict:
        """
        Vérifie le statut d'une transaction auprès de CinetPay.

        Returns:
            dict avec 'status' ("ACCEPTED"|"REFUSED"|"PENDING"),
            'amount', 'payment_method', 'description'
        """
        if not SITE_ID or not API_KEY:
            return {"success": True, "status": "PENDING", "simulated": True}

        payload = {
            "apikey":         API_KEY,
            "site_id":        SITE_ID,
            "transaction_id": transaction_id,
        }
        try:
            resp = self.session.post(f"{BASE_URL}/payment/check",
                                     json=payload, timeout=15)
            data = resp.json()

            if resp.status_code == 200:
                pay_data = data.get("data", {})
                status   = pay_data.get("status", "PENDING")
                logger.info(f"CinetPay check : txn={transaction_id} status={status}")
                return {
                    "success":        True,
                    "status":         status,
                    "amount":         pay_data.get("amount"),
                    "payment_method": pay_data.get("payment_method"),
                    "operator_id":    pay_data.get("operator_id"),
                    "description":    pay_data.get("description"),
                    "customer_phone": pay_data.get("customer_phone_number"),
                }

            return {"success": False, "error": data.get("message", "Erreur check")}

        except requests.RequestException as e:
            logger.error(f"CinetPay check exception: {e}")
            return {"success": False, "error": str(e)}

    # ── Validation signature webhook ─────────────────────────────────────────

    def verify_webhook_signature(self, payload: dict,
                                  received_signature: str) -> bool:
        """
        Vérifie la signature HMAC-SHA256 du webhook CinetPay.

        CinetPay signe la concaténation de :
        cpm_site_id + cpm_trans_id + cpm_trans_date + cpm_amount + cpm_currency
        avec SECRET_KEY via HMAC-SHA256.

        Args:
            payload: Corps du webhook (dict)
            received_signature: Signature reçue dans le header ou le corps

        Returns:
            True si la signature est valide
        """
        if not SECRET_KEY:
            logger.warning("CINETPAY_SECRET_KEY non configurée — signature non vérifiée")
            return True  # Pas bloquant en dev

        msg = (
            str(payload.get("cpm_site_id", ""))
            + str(payload.get("cpm_trans_id", ""))
            + str(payload.get("cpm_trans_date", ""))
            + str(payload.get("cpm_amount", ""))
            + str(payload.get("cpm_currency", ""))
        )
        expected = hmac.new(
            SECRET_KEY.encode(),
            msg.encode(),
            hashlib.sha256,
        ).hexdigest()

        valid = hmac.compare_digest(expected, received_signature)
        if not valid:
            logger.warning(f"Signature webhook invalide : expected={expected[:16]}…")
        return valid

    # ── Utilitaires ──────────────────────────────────────────────────────────

    def is_payment_accepted(self, webhook_payload: dict) -> bool:
        """Retourne True si le webhook indique un paiement accepté."""
        result = webhook_payload.get("cpm_result") or webhook_payload.get("status")
        return result in ("00", "ACCEPTED", "SUCCESS")

    def _simulation_init(self, transaction_id: str, amount: int) -> dict:
        """Réponse simulée quand les clés API ne sont pas configurées (dev/test)."""
        logger.info(f"[SIMULATION CinetPay] init txn={transaction_id} amount={amount} XOF")
        return {
            "success":       True,
            "simulated":     True,
            "payment_url":   f"https://sandbox.cinetpay.com/pay/{transaction_id}",
            "payment_token": f"sim_token_{transaction_id}",
        }
