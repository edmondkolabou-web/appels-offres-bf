"""
NetSync Gov — Service de gestion des abonnements
Orchestre : initiation paiement, activation plan, expiration, renouvellement.
"""
import uuid
import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.models import Abonne, Paiement
from backend.paiement.cinetpay_client import CinetPayClient

logger = logging.getLogger("netsync.subscription")

# Tarifs en FCFA
TARIFS: dict[tuple[str, str], int] = {
    ("pro",    "mensuel"): 15_000,
    ("pro",    "annuel"):  144_000,   # 15 000 × 12 × 0.80
    ("equipe", "mensuel"): 45_000,
    ("equipe", "annuel"):  432_000,   # 45 000 × 12 × 0.80
}

DESCRIPTIONS = {
    ("pro",    "mensuel"): "NetSync Gov — Plan Pro mensuel",
    ("pro",    "annuel"):  "NetSync Gov — Plan Pro annuel (-20%)",
    ("equipe", "mensuel"): "NetSync Gov — Plan Équipe mensuel",
    ("equipe", "annuel"):  "NetSync Gov — Plan Équipe annuel (-20%)",
}

CHANNEL_MAP = {
    "om":   "MOBILE_MONEY",
    "moov": "MOBILE_MONEY",
    "card": "CREDIT_CARD",
    "all":  "ALL",
}


def compute_expiry(plan: str, periode: str) -> date:
    """Calcule la date d'expiration selon plan et période."""
    today = date.today()
    if periode == "annuel":
        try:
            return today.replace(year=today.year + 1)
        except ValueError:  # 29 fév → 28 fév
            return today.replace(year=today.year + 1, day=28)
    # Mensuel : 31 jours pour couvrir tous les mois
    return today + timedelta(days=31)


class SubscriptionService:
    """
    Gère le cycle de vie complet d'un abonnement NetSync Gov.
    """

    def __init__(self, db: Session):
        self.db       = db
        self.cinetpay = CinetPayClient()

    # ── Initiation ────────────────────────────────────────────────────────────

    def initiate(
        self,
        abonne: Abonne,
        plan: str,
        periode: str,
        methode: str = "all",
    ) -> dict:
        """
        Crée une transaction de paiement et retourne l'URL de paiement.

        Args:
            abonne: Abonné qui souscrit
            plan: "pro" ou "equipe"
            periode: "mensuel" ou "annuel"
            methode: "om" | "moov" | "card" | "all"

        Returns:
            dict avec 'paiement_id', 'transaction_id', 'payment_url', 'montant'
        """
        montant = TARIFS.get((plan, periode))
        if not montant:
            raise ValueError(f"Combinaison invalide : plan={plan} periode={periode}")

        transaction_id = f"NSG-{uuid.uuid4().hex[:12].upper()}"
        description    = DESCRIPTIONS.get((plan, periode), "NetSync Gov Abonnement")
        channel        = CHANNEL_MAP.get(methode, "ALL")

        # Appel CinetPay
        cp_result = self.cinetpay.init_payment(
            transaction_id=transaction_id,
            amount=montant,
            currency="XOF",
            description=description,
            customer_name=f"{abonne.prenom} {abonne.nom}",
            customer_email=abonne.email,
            customer_phone=abonne.whatsapp or "",
            channels=channel,
            metadata=f'{{"abonne_id":"{abonne.id}","plan":"{plan}","periode":"{periode}"}}',
        )

        # Enregistrer la transaction en BDD (statut pending)
        paiement = Paiement(
            abonne_id=abonne.id,
            transaction_id=transaction_id,
            montant=montant,
            plan=plan,
            periode=periode,
            methode=methode,
            statut="pending",
            metadata_={
                "payment_url":   cp_result.get("payment_url"),
                "payment_token": cp_result.get("payment_token"),
                "cinetpay_ok":   cp_result.get("success"),
                "simulated":     cp_result.get("simulated", False),
            },
        )
        self.db.add(paiement)
        self.db.commit()
        self.db.refresh(paiement)

        logger.info(
            f"Paiement initié : {abonne.email} → {plan}/{periode} "
            f"({montant} XOF) txn={transaction_id}"
        )

        return {
            "paiement_id":   str(paiement.id),
            "transaction_id": transaction_id,
            "payment_url":   cp_result.get("payment_url"),
            "montant":       montant,
            "success":       cp_result.get("success"),
        }

    # ── Activation via webhook ────────────────────────────────────────────────

    def activate_from_webhook(self, webhook_body: dict) -> Optional[Paiement]:
        """
        Traite un webhook CinetPay et active l'abonnement si paiement accepté.
        Idempotent : ignore les transactions déjà traitées.

        Args:
            webhook_body: Corps brut du webhook CinetPay

        Returns:
            Objet Paiement mis à jour, ou None si transaction inconnue/déjà traitée
        """
        transaction_id = (
            webhook_body.get("cpm_trans_id")
            or webhook_body.get("transaction_id")
        )
        if not transaction_id:
            logger.error("Webhook CinetPay sans transaction_id")
            return None

        paiement = (
            self.db.query(Paiement)
            .filter(Paiement.transaction_id == transaction_id)
            .first()
        )
        if not paiement:
            logger.warning(f"Webhook : transaction inconnue {transaction_id}")
            return None

        # Idempotence
        if paiement.statut == "success":
            logger.info(f"Webhook : transaction déjà traitée {transaction_id}")
            return paiement

        accepted = self.cinetpay.is_payment_accepted(webhook_body)

        if accepted:
            self._activate(paiement)
            logger.info(
                f"Abonnement activé via webhook : "
                f"txn={transaction_id} plan={paiement.plan}"
            )
        else:
            paiement.statut = "failed"
            cp_status = webhook_body.get("cpm_result") or webhook_body.get("status")
            logger.warning(f"Webhook : paiement refusé txn={transaction_id} status={cp_status}")
            self.db.commit()

        return paiement

    # ── Vérification manuelle (polling) ──────────────────────────────────────

    def check_and_activate(self, transaction_id: str) -> Optional[Paiement]:
        """
        Vérifie le statut d'une transaction auprès de CinetPay
        et active l'abonnement si paiement confirmé.
        Utile pour les clients qui reviennent après paiement sans webhook.
        """
        paiement = (
            self.db.query(Paiement)
            .filter(Paiement.transaction_id == transaction_id)
            .first()
        )
        if not paiement or paiement.statut == "success":
            return paiement

        result = self.cinetpay.check_payment(transaction_id)
        if result.get("success") and result.get("status") == "ACCEPTED":
            self._activate(paiement)
            logger.info(f"Abonnement activé via polling : txn={transaction_id}")

        return paiement

    # ── Remboursement ─────────────────────────────────────────────────────────

    def refund(self, paiement: Paiement, raison: str = "Demande abonné") -> bool:
        """
        Marque un paiement comme remboursé et rétrograde l'abonné.
        Note : CinetPay ne propose pas d'API de remboursement automatique.
        Le remboursement est manuel via le dashboard CinetPay.
        """
        if paiement.statut != "success":
            logger.warning(f"Remboursement impossible : statut={paiement.statut}")
            return False

        abonne = self.db.get(Abonne, paiement.abonne_id)
        if abonne:
            abonne.plan = "gratuit"
            abonne.plan_expire_le = None

        paiement.statut = "refunded"
        self.db.commit()
        logger.info(
            f"Paiement {paiement.transaction_id} marqué remboursé. "
            f"Raison : {raison}"
        )
        return True

    # ── Expiration automatique ────────────────────────────────────────────────

    def expire_subscriptions(self) -> int:
        """
        Rétrograde les abonnés dont le plan a expiré.
        À appeler quotidiennement via Celery.
        Returns: nombre d'abonnés rétrogradés.
        """
        today = date.today()
        expired = (
            self.db.query(Abonne)
            .filter(
                Abonne.plan != "gratuit",
                Abonne.plan_expire_le.isnot(None),
                Abonne.plan_expire_le < today,
            )
            .all()
        )

        for abonne in expired:
            logger.info(
                f"Abonnement expiré : {abonne.email} "
                f"(plan={abonne.plan}, expiré le {abonne.plan_expire_le})"
            )
            abonne.plan = "gratuit"
            abonne.plan_expire_le = None

        if expired:
            self.db.commit()

        logger.info(f"Expirations : {len(expired)} abonné(s) rétrogradé(s)")
        return len(expired)

    # ── Reset compteur quotidien ──────────────────────────────────────────────

    def reset_daily_counters(self) -> None:
        """
        Remet à zéro le compteur de consultations quotidiennes (Plan Gratuit).
        À appeler chaque nuit à 00h00 via Celery.
        """
        self.db.execute(
            text("UPDATE abonnes SET ao_consultes_auj = 0 WHERE ao_consultes_auj > 0")
        )
        self.db.commit()
        logger.info("Compteurs quotidiens réinitialisés")

    # ── Interne ───────────────────────────────────────────────────────────────

    def _activate(self, paiement: Paiement) -> None:
        """Active le plan de l'abonné et met à jour le paiement."""
        abonne = self.db.get(Abonne, paiement.abonne_id)
        if not abonne:
            logger.error(f"Activation impossible : abonné {paiement.abonne_id} introuvable")
            return

        expiry = compute_expiry(paiement.plan, paiement.periode)
        paiement.statut   = "success"
        paiement.expire_le = expiry
        abonne.plan          = paiement.plan
        abonne.plan_expire_le = expiry
        self.db.commit()

        # Envoyer email de confirmation
        try:
            from alertes_netsync_gov.email_sender import ResendClient
            from alertes_netsync_gov.email_templates import render_bienvenue
            mailer = ResendClient()
            subject, html = render_bienvenue(
                prenom=abonne.prenom,
                plan=paiement.plan,
                secteurs=[],
            )
            mailer.send(abonne.email, subject, html,
                        tags=[{"name": "type", "value": "activation_abonnement"}])
        except Exception as e:
            logger.warning(f"Email confirmation non envoyé : {e}")
