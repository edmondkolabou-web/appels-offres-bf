"""
NetSync Gov — Moteur d'alertes principal (refactorisé étape 11)
Orchestre email + WhatsApp avec logs, déduplication et métriques.
"""
import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text, func

from backend.models import AppelOffre, Abonne, PreferenceAlerte, EnvoiAlerte
from backend.alertes.whatsapp import AOAlertWhatsApp
from backend.alertes.email_sender import ResendClient
from backend.alertes.email_templates import render_nouvel_ao, render_rappel_j3, render_bienvenue
from backend.alertes.composables_alerts import build_ao_email_context

logger = logging.getLogger("netsync.alert_engine")


class AlertEngine:
    """
    Moteur d'alertes central — version production.

    Orchestration :
    1. Trouver les abonnés correspondant à l'AO (requête SQL optimisée GIN)
    2. Vérifier déduplication (envoi déjà fait pour ce couple abonné+ao+canal)
    3. Préparer le contenu selon le template (email HTML / WA template)
    4. Envoyer via Resend ou WhatsApp Business API
    5. Logger le résultat dans envois_alertes
    """

    def __init__(self, db: Session):
        self.db     = db
        self.wa     = AOAlertWhatsApp()
        self.mailer = ResendClient()
        self._stats = {"email_ok": 0, "email_fail": 0, "wa_ok": 0, "wa_fail": 0, "ignores": 0}

    # ── Traitement d'un nouvel AO ────────────────────────────────────────────

    def process_new_ao(self, ao: AppelOffre) -> int:
        """
        Envoie les alertes pour un AO nouvellement inséré.
        Returns: nombre total d'alertes envoyées.
        """
        abonnes = self._find_matching_abonnes(ao, type_alerte="nouveau_ao")
        logger.info(f"AO {ao.reference} → {len(abonnes)} abonné(s) à alerter")

        sent = 0
        for abonne, canal in abonnes:
            sent += self._dispatch(ao, abonne, canal, "nouveau_ao")

        return sent

    # ── Rappels J-3 ─────────────────────────────────────────────────────────

    def process_rappels_j3(self) -> int:
        """
        Envoie les rappels pour les AO clôturant dans exactement 3 jours.
        """
        target = date.today() + timedelta(days=3)
        ao_list = (
            self.db.query(AppelOffre)
            .filter(
                AppelOffre.statut == "ouvert",
                AppelOffre.date_cloture == target,
            )
            .all()
        )
        logger.info(f"Rappels J-3 : {len(ao_list)} AO clôturent le {target}")

        total = 0
        for ao in ao_list:
            abonnes = self._find_matching_abonnes(ao, type_alerte="rappel_j3")
            for abonne, canal in abonnes:
                pref = (
                    self.db.query(PreferenceAlerte)
                    .filter(PreferenceAlerte.abonne_id == abonne.id,
                            PreferenceAlerte.actif == True)
                    .first()
                )
                if pref and pref.rappel_j3:
                    total += self._dispatch(ao, abonne, canal, "rappel_j3")

        return total

    # ── Bienvenue nouvel abonné ──────────────────────────────────────────────

    def send_bienvenue(self, abonne: Abonne, secteurs: list) -> None:
        """Envoie un email + WA de bienvenue après inscription."""
        # Email
        subject, html = render_bienvenue(abonne.prenom, abonne.plan, secteurs)
        self.mailer.send(abonne.email, subject, html,
                         tags=[{"name": "type", "value": "bienvenue"}])
        # WhatsApp si numéro fourni
        if abonne.whatsapp:
            self.wa.send_bienvenue(abonne)

    # ── Dispatch selon canal ─────────────────────────────────────────────────

    def _dispatch(self, ao: AppelOffre, abonne: Abonne,
                  canal: str, type_alerte: str) -> int:
        """Envoie sur le(s) canal(aux) et logue le résultat."""
        sent = 0

        if canal in ("email", "les_deux") and abonne.email:
            ok = self._send_email(ao, abonne, type_alerte)
            self._log(ao, abonne, "email", type_alerte, ok)
            if ok:
                sent += 1
                self._stats["email_ok"] += 1
            else:
                self._stats["email_fail"] += 1

        if canal in ("whatsapp", "les_deux") and abonne.whatsapp:
            ok = self._send_whatsapp(ao, abonne, type_alerte)
            self._log(ao, abonne, "whatsapp", type_alerte, ok)
            if ok:
                sent += 1
                self._stats["wa_ok"] += 1
            else:
                self._stats["wa_fail"] += 1

        return sent

    def _send_email(self, ao: AppelOffre, abonne: Abonne,
                    type_alerte: str) -> bool:
        """Prépare et envoie l'email."""
        ao_url = f"https://gov.netsync.bf/aos/{ao.id}"
        ctx    = build_ao_email_context(ao)
        try:
            if type_alerte == "rappel_j3":
                subject, html = render_rappel_j3(
                    prenom=abonne.prenom,
                    ao_titre=ao.titre,
                    ao_reference=ao.reference,
                    autorite=ao.autorite_contractante or "",
                    date_cloture=ctx["date_cloture"] or "—",
                    jours_restants=ao.jours_restants or 3,
                    ao_url=ao_url,
                )
            else:
                subject, html = render_nouvel_ao(
                    prenom=abonne.prenom,
                    ao_url=ao_url,
                    est_urgent=ao.est_urgent,
                    jours_restants=ao.jours_restants,
                    **ctx,
                )
            tags = [
                {"name": "type",      "value": type_alerte},
                {"name": "secteur",   "value": ao.secteur},
                {"name": "abonne_id", "value": str(abonne.id)},
            ]
            result = self.mailer.send(abonne.email, subject, html, tags=tags)
            return result.get("success", False)
        except Exception as e:
            logger.error(f"Email exception ({abonne.email}, ao={ao.reference}): {e}")
            return False

    def _send_whatsapp(self, ao: AppelOffre, abonne: Abonne,
                       type_alerte: str) -> bool:
        """Envoie la notification WhatsApp."""
        try:
            if type_alerte == "rappel_j3":
                result = self.wa.send_rappel_j3(abonne, ao)
            else:
                result = self.wa.send_nouvel_ao(abonne, ao)
            return result.get("success", False)
        except Exception as e:
            logger.error(f"WA exception ({abonne.whatsapp}, ao={ao.reference}): {e}")
            return False

    # ── Requête matching abonnés ─────────────────────────────────────────────

    def _find_matching_abonnes(self, ao: AppelOffre,
                                type_alerte: str) -> list[tuple[Abonne, str]]:
        """
        SQL optimisé : trouve les abonnés Pro actifs dont les préférences
        correspondent au secteur de l'AO, sans doublon d'envoi.
        Utilise l'index GIN sur preferences_alertes.secteurs[].
        """
        rows = self.db.execute(
            text("""
                SELECT
                    a.id       AS abonne_id,
                    p.canal    AS canal,
                    p.mots_cles AS mots_cles
                FROM abonnes a
                JOIN preferences_alertes p ON p.abonne_id = a.id
                WHERE a.plan != 'gratuit'
                  AND a.actif  = true
                  AND p.actif  = true
                  AND (
                        :secteur = ANY(p.secteurs)
                     OR array_length(p.secteurs, 1) IS NULL
                     OR p.secteurs = ARRAY[]::varchar[]
                  )
                  AND (
                        p.sources = ARRAY[]::varchar[]
                     OR p.sources IS NULL
                     OR :source = ANY(p.sources)
                  )
                  AND NOT EXISTS (
                        SELECT 1 FROM envois_alertes e
                        WHERE e.abonne_id    = a.id
                          AND e.ao_id        = :ao_id
                          AND e.type_alerte  = :type_alerte
                  )
            """),
            {
                "secteur":     ao.secteur,
                "source":      ao.source,
                "ao_id":       str(ao.id),
                "type_alerte": type_alerte,
            },
        ).fetchall()

        result = []
        for row in rows:
            abonne = self.db.get(Abonne, row.abonne_id)
            if not abonne:
                continue
            # Filtre mots-clés si secteur ne match pas directement
            mots_cles = row.mots_cles or []
            if mots_cles:
                texte = f"{ao.titre} {ao.description or ''}".lower()
                if not any(kw.lower() in texte for kw in mots_cles):
                    self._stats["ignores"] += 1
                    continue
            result.append((abonne, row.canal))
        return result

    # ── Log ──────────────────────────────────────────────────────────────────

    def _log(self, ao: AppelOffre, abonne: Abonne,
             canal: str, type_alerte: str, success: bool) -> None:
        """Enregistre le résultat d'un envoi dans envois_alertes."""
        try:
            envoi = EnvoiAlerte(
                abonne_id=abonne.id,
                ao_id=ao.id,
                canal=canal,
                statut="envoye" if success else "echec",
                type_alerte=type_alerte,
                tentatives=1,
            )
            self.db.add(envoi)
            self.db.flush()
        except Exception as e:
            logger.error(f"Log envoi échoué : {e}")

    def get_stats(self) -> dict:
        return dict(self._stats)
