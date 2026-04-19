"""
NetSync Gov — Utilitaires partagés pour les alertes.
"""
from datetime import date
from typing import Optional
from backend.models import AppelOffre


def build_ao_email_context(ao: AppelOffre) -> dict:
    """Construit le contexte commun pour les templates email."""
    MOIS = ['janv.','févr.','mars','avr.','mai','juin',
            'juil.','août','sept.','oct.','nov.','déc.']

    def fmt_date(d: Optional[date]) -> Optional[str]:
        if not d:
            return None
        return f"{d.day} {MOIS[d.month-1]} {d.year}"

    def fmt_montant(v: Optional[int]) -> Optional[str]:
        if not v:
            return None
        if v >= 1_000_000_000:
            return f"{v/1_000_000_000:.1f} Mrd FCFA"
        if v >= 1_000_000:
            return f"{v/1_000_000:.0f} M FCFA"
        if v >= 1_000:
            return f"{v/1_000:.0f} K FCFA"
        return f"{v:,} FCFA"

    return {
        "ao_titre":       ao.titre,
        "ao_reference":   ao.reference,
        "autorite":       ao.autorite_contractante or "Non précisée",
        "type_procedure": ao.type_procedure or "ouvert",
        "secteur":        ao.secteur or "autre",
        "date_publication": fmt_date(ao.date_publication) or "—",
        "date_cloture":   fmt_date(ao.date_cloture),
        "montant":        fmt_montant(ao.montant_estime),
        "source":         ao.source or "dgcmef",
    }
