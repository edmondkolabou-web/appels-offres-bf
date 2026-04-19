"""
NetSync Gov — Router : Paiements CinetPay
POST /paiements/initier     → créer une transaction CinetPay
GET  /paiements/historique  → historique des paiements
POST /paiements/webhook     → callback CinetPay (public)
GET  /paiements/statut/{id} → vérifier le statut d'une transaction
"""
import os
import logging
from datetime import date, timedelta
from uuid import UUID

import requests
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from database import get_db
from models import Abonne, Paiement
from schemas import PaiementIn, PaiementOut
from security import get_current_abonne

router = APIRouter()
logger = logging.getLogger("netsync.paiements")

CINETPAY_SITE_ID    = os.getenv("CINETPAY_SITE_ID", "")
CINETPAY_API_KEY    = os.getenv("CINETPAY_API_KEY", "")
CINETPAY_SECRET_KEY = os.getenv("CINETPAY_SECRET_KEY", "")
CINETPAY_NOTIFY_URL = os.getenv("CINETPAY_NOTIFY_URL", "https://api.gov.netsync.bf/api/v1/paiements/webhook")

TARIFS = {
    ("pro",    "mensuel"): 15_000,
    ("pro",    "annuel"):  144_000,
    ("equipe", "mensuel"): 45_000,
    ("equipe", "annuel"):  432_000,
}


def _compute_expiry(plan: str, periode: str) -> date:
    """Calcule la date d'expiration selon le plan et la période."""
    today = date.today()
    if periode == "annuel":
        return today.replace(year=today.year + 1)
    if plan == "equipe":
        return today + timedelta(days=31)
    return today + timedelta(days=31)


@router.post("/initier", response_model=PaiementOut, status_code=status.HTTP_201_CREATED)
def initier_paiement(
    body:    PaiementIn,
    db:      Session = Depends(get_db),
    current: Abonne  = Depends(get_current_abonne),
):
    """
    Initie une transaction de paiement CinetPay.
    Retourne les détails de la transaction (dont l'URL de paiement en metadata).
    """
    montant = TARIFS.get((body.plan, body.periode))
    if not montant:
        raise HTTPException(status_code=400, detail="Combinaison plan/période invalide")

    import uuid as _uuid
    transaction_id = f"NSG-{_uuid.uuid4().hex[:12].upper()}"

    # Appel API CinetPay
    payment_url = None
    if CINETPAY_SITE_ID and CINETPAY_API_KEY:
        try:
            resp = requests.post(
                "https://api-checkout.cinetpay.com/v2/payment",
                json={
                    "apikey": CINETPAY_API_KEY,
                    "site_id": CINETPAY_SITE_ID,
                    "transaction_id": transaction_id,
                    "amount": montant,
                    "currency": "XOF",
                    "description": f"NetSync Gov — Plan {body.plan.title()} ({body.periode})",
                    "customer_name": f"{current.prenom} {current.nom}",
                    "customer_email": current.email,
                    "customer_phone_number": current.whatsapp or "",
                    "notify_url": CINETPAY_NOTIFY_URL,
                    "return_url": "https://gov.netsync.bf/paiement/succes",
                    "channels": "ALL",
                    "lang": "fr",
                },
                timeout=20,
            )
            if resp.status_code == 200:
                data = resp.json()
                payment_url = data.get("data", {}).get("payment_url")
        except requests.RequestException as e:
            logger.error(f"Erreur CinetPay initiation : {e}")

    paiement = Paiement(
        abonne_id=current.id,
        transaction_id=transaction_id,
        montant=montant,
        plan=body.plan,
        periode=body.periode,
        methode=body.methode,
        statut="pending",
        metadata_={"payment_url": payment_url} if payment_url else {},
        expire_le=None,
    )
    db.add(paiement)
    db.commit()
    db.refresh(paiement)
    return PaiementOut.model_validate(paiement)


@router.get("/historique", response_model=list[PaiementOut])
def historique_paiements(
    db:      Session = Depends(get_db),
    current: Abonne  = Depends(get_current_abonne),
):
    """Historique des transactions de l'abonné connecté."""
    paiements = (
        db.query(Paiement)
        .filter(Paiement.abonne_id == current.id)
        .order_by(Paiement.created_at.desc())
        .limit(50)
        .all()
    )
    return [PaiementOut.model_validate(p) for p in paiements]


@router.get("/statut/{transaction_id}")
def check_statut(
    transaction_id: str,
    db:             Session = Depends(get_db),
    current:        Abonne  = Depends(get_current_abonne),
):
    """Vérifie le statut d'une transaction en interrogeant CinetPay."""
    paiement = (
        db.query(Paiement)
        .filter(
            Paiement.transaction_id == transaction_id,
            Paiement.abonne_id == current.id,
        )
        .first()
    )
    if not paiement:
        raise HTTPException(status_code=404, detail="Transaction introuvable")

    # Vérifier en temps réel auprès de CinetPay
    if CINETPAY_API_KEY and paiement.statut == "pending":
        try:
            resp = requests.post(
                "https://api-checkout.cinetpay.com/v2/payment/check",
                json={
                    "apikey": CINETPAY_API_KEY,
                    "site_id": CINETPAY_SITE_ID,
                    "transaction_id": transaction_id,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                if data.get("status") == "ACCEPTED":
                    _activate_subscription(paiement, current, db)
        except requests.RequestException as e:
            logger.warning(f"Check CinetPay échoué : {e}")

    return PaiementOut.model_validate(paiement)


@router.post("/webhook")
async def cinetpay_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Webhook CinetPay — appelé automatiquement lors de la confirmation du paiement.
    Idempotent : vérifie si la transaction est déjà traitée.
    """
    body = await request.json()
    transaction_id = body.get("cpm_trans_id") or body.get("transaction_id")
    cp_status      = body.get("cpm_result") or body.get("status")

    if not transaction_id:
        raise HTTPException(status_code=400, detail="transaction_id manquant")

    paiement = (
        db.query(Paiement)
        .filter(Paiement.transaction_id == transaction_id)
        .first()
    )
    if not paiement:
        logger.warning(f"Webhook CinetPay : transaction inconnue {transaction_id}")
        return {"status": "ignored"}

    # Idempotence : déjà traité
    if paiement.statut == "success":
        return {"status": "already_processed"}

    if cp_status in ("00", "ACCEPTED", "SUCCESS"):
        abonne = db.get(Abonne, paiement.abonne_id)
        if abonne:
            _activate_subscription(paiement, abonne, db)
        logger.info(f"Webhook : paiement {transaction_id} accepté — plan activé")
    else:
        paiement.statut = "failed"
        db.commit()
        logger.warning(f"Webhook : paiement {transaction_id} refusé (status={cp_status})")

    return {"status": "ok"}


def _activate_subscription(paiement: Paiement, abonne: Abonne, db: Session):
    """Met à jour le plan de l'abonné et marque la transaction comme réussie."""
    paiement.statut   = "success"
    paiement.expire_le = _compute_expiry(paiement.plan, paiement.periode)
    abonne.plan          = paiement.plan
    abonne.plan_expire_le = paiement.expire_le
    db.commit()
    logger.info(f"Abonnement activé : {abonne.email} → {paiement.plan} jusqu'au {paiement.expire_le}")
