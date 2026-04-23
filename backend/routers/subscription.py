"""
NetSync Gov — Router : Gestion des abonnements (cycle de vie complet)
GET  /subscription/status       → état actuel de l'abonnement
POST /subscription/trial        → activer la période d'essai (7 jours)
POST /subscription/upgrade      → passer à un plan supérieur
POST /subscription/downgrade    → rétrograder
POST /subscription/cancel       → annuler l'abonnement
GET  /subscription/invoices     → liste des factures
GET  /subscription/invoice/{id} → télécharger une facture PDF
"""
import uuid
import logging
from datetime import date, timedelta, datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import get_db
from backend.models import Abonne, Paiement
from backend.security import get_current_abonne

logger = logging.getLogger("netsync.subscription")
router = APIRouter()

TARIFS = {
    ("pro", "mensuel"): 15_000,
    ("pro", "annuel"): 144_000,
    ("equipe", "mensuel"): 45_000,
    ("equipe", "annuel"): 432_000,
}

PLAN_LIMITES = {
    "gratuit": {"ao_par_jour": 3, "alertes": 0, "favoris": 10},
    "pro": {"ao_par_jour": -1, "alertes": 10, "favoris": -1},
    "equipe": {"ao_par_jour": -1, "alertes": 50, "favoris": -1},
    "institutionnel": {"ao_par_jour": -1, "alertes": -1, "favoris": -1},
}


# ── Schemas ────────────────────────────────────────────────────────────────────
class SubscriptionStatus(BaseModel):
    plan: str
    periode: Optional[str] = None
    actif: bool
    est_pro: bool
    trial_actif: bool
    trial_expire_le: Optional[date] = None
    plan_expire_le: Optional[date] = None
    jours_restants: Optional[int] = None
    nb_renouvellements: int = 0
    limites: dict
    montant_mensuel: Optional[int] = None

class TrialResponse(BaseModel):
    message: str
    trial_expire_le: date
    plan: str

class UpgradeRequest(BaseModel):
    plan: str
    periode: str = "mensuel"

class InvoiceOut(BaseModel):
    id: str
    date: datetime
    montant: int
    plan: str
    periode: str
    statut: str
    reference: str


# ── Status ─────────────────────────────────────────────────────────────────────
@router.get("/status", response_model=SubscriptionStatus)
def subscription_status(current: Abonne = Depends(get_current_abonne)):
    """Retourne l'état complet de l'abonnement."""
    jours = None
    if current.plan_expire_le:
        jours = (current.plan_expire_le - date.today()).days
        if jours < 0:
            jours = 0

    montant = TARIFS.get((current.plan, current.plan_periode or "mensuel"))

    return SubscriptionStatus(
        plan=current.plan,
        periode=current.plan_periode,
        actif=current.actif,
        est_pro=current.est_pro,
        trial_actif=current.trial_actif or False,
        trial_expire_le=current.trial_expire_le,
        plan_expire_le=current.plan_expire_le,
        jours_restants=jours,
        nb_renouvellements=current.nb_renouvellements or 0,
        limites=PLAN_LIMITES.get(current.plan, PLAN_LIMITES["gratuit"]),
        montant_mensuel=montant,
    )


# ── Trial ──────────────────────────────────────────────────────────────────────
@router.post("/trial", response_model=TrialResponse)
def start_trial(
    db: Session = Depends(get_db),
    current: Abonne = Depends(get_current_abonne),
):
    """Active une période d'essai Pro de 7 jours (une seule fois par compte)."""
    if current.plan != "gratuit":
        raise HTTPException(status_code=400, detail="Vous avez déjà un plan actif")

    if current.trial_actif or current.trial_expire_le:
        raise HTTPException(status_code=400, detail="Vous avez déjà utilisé votre période d'essai")

    current.plan = "pro"
    current.trial_actif = True
    current.trial_expire_le = date.today() + timedelta(days=7)
    current.plan_expire_le = date.today() + timedelta(days=7)
    current.plan_periode = "mensuel"
    db.commit()

    logger.info(f"Trial activé pour {current.email} — expire le {current.trial_expire_le}")

    return TrialResponse(
        message="Période d'essai Pro activée pour 7 jours. Profitez-en !",
        trial_expire_le=current.trial_expire_le,
        plan="pro",
    )


# ── Upgrade ────────────────────────────────────────────────────────────────────
@router.post("/upgrade")
def upgrade_plan(
    body: UpgradeRequest,
    db: Session = Depends(get_db),
    current: Abonne = Depends(get_current_abonne),
):
    """Upgrade vers un plan supérieur. Retourne les infos de paiement."""
    if body.plan not in ("pro", "equipe", "institutionnel"):
        raise HTTPException(status_code=400, detail="Plan invalide")

    if body.periode not in ("mensuel", "annuel"):
        raise HTTPException(status_code=400, detail="Période invalide (mensuel ou annuel)")

    montant = TARIFS.get((body.plan, body.periode))
    if not montant:
        raise HTTPException(status_code=400, detail="Combinaison plan/période invalide")

    plan_order = {"gratuit": 0, "pro": 1, "equipe": 2, "institutionnel": 3}
    if plan_order.get(body.plan, 0) <= plan_order.get(current.plan, 0):
        if not current.trial_actif:
            raise HTTPException(status_code=400, detail="Ce plan n'est pas un upgrade")

    return {
        "message": f"Pour passer au plan {body.plan} ({body.periode}), procédez au paiement",
        "montant": montant,
        "devise": "XOF",
        "plan": body.plan,
        "periode": body.periode,
        "endpoint_paiement": "/api/v1/paiements/initier",
    }


# ── Downgrade ──────────────────────────────────────────────────────────────────
@router.post("/downgrade")
def downgrade_plan(
    db: Session = Depends(get_db),
    current: Abonne = Depends(get_current_abonne),
):
    """Rétrograde vers le plan gratuit à la fin de la période en cours."""
    if current.plan == "gratuit":
        raise HTTPException(status_code=400, detail="Vous êtes déjà sur le plan gratuit")

    return {
        "message": f"Votre plan {current.plan} reste actif jusqu'au {current.plan_expire_le}. "
                   f"Après cette date, vous passerez automatiquement au plan gratuit.",
        "plan_actuel": current.plan,
        "expire_le": str(current.plan_expire_le) if current.plan_expire_le else "Non défini",
    }


# ── Cancel ─────────────────────────────────────────────────────────────────────
@router.post("/cancel")
def cancel_subscription(
    db: Session = Depends(get_db),
    current: Abonne = Depends(get_current_abonne),
):
    """Annule l'abonnement immédiatement et passe au plan gratuit."""
    if current.plan == "gratuit":
        raise HTTPException(status_code=400, detail="Pas d'abonnement actif à annuler")

    old_plan = current.plan
    current.plan = "gratuit"
    current.trial_actif = False
    current.plan_expire_le = None
    current.plan_periode = None
    db.commit()

    logger.info(f"Abonnement annulé: {current.email} ({old_plan} → gratuit)")

    return {
        "message": f"Abonnement {old_plan} annulé. Vous êtes maintenant sur le plan gratuit.",
        "plan": "gratuit",
    }


# ── Invoices ───────────────────────────────────────────────────────────────────
@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(
    db: Session = Depends(get_db),
    current: Abonne = Depends(get_current_abonne),
):
    """Liste les factures de l'abonné."""
    paiements = (
        db.query(Paiement)
        .filter(Paiement.abonne_id == current.id)
        .filter(Paiement.statut == "accepte")
        .order_by(Paiement.created_at.desc())
        .all()
    )

    return [
        InvoiceOut(
            id=str(p.id),
            date=p.created_at,
            montant=p.montant,
            plan=p.plan or "pro",
            periode=p.periode or "mensuel",
            statut="payée",
            reference=f"NSGOV-{p.created_at.strftime('%Y%m')}-{str(p.id)[:8].upper()}",
        )
        for p in paiements
    ]


# ── Invoice PDF ────────────────────────────────────────────────────────────────
@router.get("/invoice/{paiement_id}")
def download_invoice(
    paiement_id: str,
    db: Session = Depends(get_db),
    current: Abonne = Depends(get_current_abonne),
):
    """Génère et télécharge une facture PDF."""
    paiement = db.query(Paiement).filter(
        Paiement.id == paiement_id,
        Paiement.abonne_id == current.id,
    ).first()

    if not paiement:
        raise HTTPException(status_code=404, detail="Facture introuvable")

    pdf_bytes = _generate_invoice_pdf(paiement, current)

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=facture_netsync_gov_{str(paiement.id)[:8]}.pdf"
        },
    )


def _generate_invoice_pdf(paiement: Paiement, abonne: Abonne) -> bytes:
    """Génère une facture PDF simple."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4

    # Header
    c.setFillColor(HexColor("#0082C9"))
    c.rect(0, h - 3*cm, w, 3*cm, fill=1)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 20)
    c.drawString(2*cm, h - 2*cm, "NetSync Gov")
    c.setFont("Helvetica", 10)
    c.drawString(2*cm, h - 2.6*cm, "Facture")

    # Référence
    ref = f"NSGOV-{paiement.created_at.strftime('%Y%m')}-{str(paiement.id)[:8].upper()}"
    c.setFillColor(HexColor("#0C1B2A"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, h - 4.5*cm, f"Facture N° {ref}")
    c.setFont("Helvetica", 10)
    c.drawString(2*cm, h - 5.2*cm, f"Date : {paiement.created_at.strftime('%d/%m/%Y')}")

    # Client
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, h - 7*cm, "Client")
    c.setFont("Helvetica", 10)
    y = h - 7.6*cm
    c.drawString(2*cm, y, f"{abonne.prenom or ''} {abonne.nom or ''}")
    y -= 0.5*cm
    c.drawString(2*cm, y, f"{abonne.email}")
    y -= 0.5*cm
    if abonne.entreprise:
        c.drawString(2*cm, y, f"{abonne.entreprise}")
        y -= 0.5*cm

    # Émetteur
    c.setFont("Helvetica-Bold", 11)
    c.drawString(11*cm, h - 7*cm, "Émetteur")
    c.setFont("Helvetica", 10)
    c.drawString(11*cm, h - 7.6*cm, "NetSync Africa")
    c.drawString(11*cm, h - 8.1*cm, "Ouagadougou, Burkina Faso")
    c.drawString(11*cm, h - 8.6*cm, "edmondkolabou@gmail.com")

    # Tableau
    y = h - 10.5*cm
    c.setFillColor(HexColor("#0082C9"))
    c.rect(2*cm, y, w - 4*cm, 0.8*cm, fill=1)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(2.3*cm, y + 0.25*cm, "Description")
    c.drawString(11*cm, y + 0.25*cm, "Période")
    c.drawString(14*cm, y + 0.25*cm, "Montant")

    y -= 0.8*cm
    c.setFillColor(HexColor("#0C1B2A"))
    c.setFont("Helvetica", 9)
    plan_label = f"Plan {(paiement.plan or 'Pro').capitalize()}"
    periode_label = (paiement.periode or "mensuel").capitalize()
    c.drawString(2.3*cm, y + 0.25*cm, f"Abonnement NetSync Gov — {plan_label}")
    c.drawString(11*cm, y + 0.25*cm, periode_label)
    c.drawRightString(w - 2.3*cm, y + 0.25*cm, f"{paiement.montant:,} FCFA".replace(",", " "))

    # Ligne séparation
    y -= 0.3*cm
    c.setStrokeColor(HexColor("#DEE2E6"))
    c.line(2*cm, y, w - 2*cm, y)

    # Total
    y -= 0.8*cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(11*cm, y, "Total TTC :")
    c.setFillColor(HexColor("#0082C9"))
    c.drawRightString(w - 2.3*cm, y, f"{paiement.montant:,} FCFA".replace(",", " "))

    # Statut
    y -= 1.5*cm
    c.setFillColor(HexColor("#1D9E75"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y, "PAYÉE")
    c.setFillColor(HexColor("#6B7280"))
    c.setFont("Helvetica", 9)
    c.drawString(5*cm, y, f"Transaction: {paiement.transaction_id or 'N/A'}")

    # Footer
    c.setFillColor(HexColor("#6B7280"))
    c.setFont("Helvetica", 8)
    c.drawCentredString(w/2, 2*cm, "NetSync Gov — Un produit NetSync Africa | Ouagadougou, Burkina Faso")
    c.drawCentredString(w/2, 1.5*cm, "Ce document tient lieu de facture. Merci pour votre confiance.")

    c.save()
    return buffer.getvalue()
