"""
NetSync Gov — Étape 6 : Moteur d'alertes
Envoie les alertes email et WhatsApp pour les nouveaux AOs.
"""
import logging
import json
from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

import requests
from sqlalchemy.orm import Session
from sqlalchemy import text

from pipeline.models import AppelOffre, Abonne, PreferenceAlerte, EnvoiAlerte
from pipeline.config import config

logger = logging.getLogger("netsync.alerts")


class EmailSender:
    """Envoi d'emails via l'API Resend."""

    BASE_URL = "https://api.resend.com/emails"

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {config.RESEND_API_KEY}",
            "Content-Type": "application/json",
        }

    def send(self, to: str, subject: str, html: str) -> bool:
        """Envoie un email et retourne True si succès."""
        if not config.RESEND_API_KEY:
            logger.warning("RESEND_API_KEY non configurée — email simulé")
            logger.info(f"[SIMULÉ] Email → {to} | Sujet: {subject}")
            return True

        try:
            resp = requests.post(
                self.BASE_URL,
                headers=self.headers,
                json={
                    "from": config.RESEND_FROM_EMAIL,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                },
                timeout=15,
            )
            if resp.status_code in (200, 201):
                logger.info(f"Email envoyé → {to}")
                return True
            else:
                logger.error(f"Erreur Resend {resp.status_code} → {to} : {resp.text}")
                return False
        except requests.RequestException as e:
            logger.error(f"Exception email → {to} : {e}")
            return False

    def render_ao_alert(self, ao: AppelOffre, abonne: Abonne) -> tuple[str, str]:
        """Génère le sujet et le contenu HTML de l'alerte AO."""
        urgent_badge = (
            f'<span style="color:#A32D2D;font-weight:bold;">⚡ {ao.jours_restants}j restants</span>'
            if ao.est_urgent else ""
        )
        subject = f"[NetSync Gov] Nouveau AO — {ao.secteur.upper()} · {ao.titre[:60]}"
        html = f"""
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:'Segoe UI',Arial,sans-serif;background:#F7F9FB;margin:0;padding:20px;">
  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08);">
    <div style="background:#0F1923;padding:20px 24px;display:flex;align-items:center;gap:12px;">
      <div style="background:#0082C9;width:36px;height:36px;border-radius:8px;"></div>
      <span style="color:#fff;font-size:18px;font-weight:600;">NetSync Gov</span>
      <span style="color:rgba(255,255,255,.4);font-size:12px;">Appels d'offres BF</span>
    </div>
    <div style="padding:24px;">
      <p style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:#0082C9;margin:0 0 8px;">
        🔔 Nouveau appel d'offres — {ao.secteur.title()}
      </p>
      <h2 style="font-size:16px;color:#0F1923;margin:0 0 6px;line-height:1.4;">{ao.titre}</h2>
      <p style="font-family:monospace;font-size:11px;color:#64748B;margin:0 0 16px;">
        Réf. {ao.reference}
      </p>
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <tr style="border-bottom:1px solid #E2E8F0;">
          <td style="padding:8px 0;color:#64748B;width:40%;">Autorité</td>
          <td style="padding:8px 0;color:#0F1923;font-weight:500;">{ao.autorite_contractante}</td>
        </tr>
        <tr style="border-bottom:1px solid #E2E8F0;">
          <td style="padding:8px 0;color:#64748B;">Procédure</td>
          <td style="padding:8px 0;color:#0F1923;">{ao.type_procedure.upper()}</td>
        </tr>
        <tr style="border-bottom:1px solid #E2E8F0;">
          <td style="padding:8px 0;color:#64748B;">Publication</td>
          <td style="padding:8px 0;color:#0F1923;">{ao.date_publication.strftime("%d/%m/%Y") if ao.date_publication else "—"}</td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#64748B;">Clôture</td>
          <td style="padding:8px 0;color:#A32D2D;font-weight:600;">
            {ao.date_cloture.strftime("%d/%m/%Y") if ao.date_cloture else "Non précisée"}
            {urgent_badge}
          </td>
        </tr>
      </table>
      <div style="margin-top:20px;text-align:center;">
        <a href="https://gov.netsync.bf/ao/{ao.id}"
           style="display:inline-block;background:#0082C9;color:#fff;padding:11px 28px;border-radius:8px;text-decoration:none;font-size:14px;font-weight:500;">
          Voir le détail →
        </a>
      </div>
      <p style="font-size:11px;color:#94A3B8;margin-top:20px;text-align:center;">
        Bonjour {abonne.prenom}, cette alerte correspond à vos critères secteur <strong>{ao.secteur}</strong>.<br>
        <a href="https://gov.netsync.bf/alertes" style="color:#0082C9;">Gérer mes alertes</a> ·
        <a href="https://gov.netsync.bf/desabonner" style="color:#94A3B8;">Se désabonner</a>
      </p>
    </div>
  </div>
</body>
</html>"""
        return subject, html


class WhatsAppSender:
    """Envoi de messages via l'API WhatsApp Business (Meta Cloud API)."""

    BASE_URL = "https://graph.facebook.com/v18.0/{phone_id}/messages"

    def __init__(self):
        self.phone_id = config.WHATSAPP_PHONE_ID
        self.token = config.WHATSAPP_API_TOKEN

    def send(self, to: str, ao: AppelOffre, type_alerte: str = "nouveau_ao") -> bool:
        """
        Envoie un message WhatsApp via template ou message libre.

        Pour les messages marketing/alertes, WhatsApp Business API
        requiert des templates pré-approuvés par Meta.
        """
        if not self.token or not self.phone_id:
            logger.warning("WhatsApp API non configurée — message simulé")
            logger.info(f"[SIMULÉ] WA → {to} | AO: {ao.titre[:50]}")
            return True

        # Nettoyer le numéro (supprimer +, espaces)
        phone = re.sub(r"[^\d]", "", to)
        if phone.startswith("0") and len(phone) == 9:
            phone = "226" + phone[1:]  # Préfixe Burkina

        # Format message texte simple (template libre en 24h window)
        body = self._format_message(ao, type_alerte)

        url = self.BASE_URL.format(phone_id=self.phone_id)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": body, "preview_url": False},
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            if resp.status_code == 200:
                logger.info(f"WhatsApp envoyé → {phone}")
                return True
            else:
                logger.error(f"Erreur WA {resp.status_code} → {phone}: {resp.text}")
                return False
        except requests.RequestException as e:
            logger.error(f"Exception WA → {phone}: {e}")
            return False

    def _format_message(self, ao: AppelOffre, type_alerte: str) -> str:
        """Formate le message WhatsApp selon le type d'alerte."""
        import re
        if type_alerte == "rappel_j3":
            return (
                f"⏰ *Rappel clôture J-{ao.jours_restants}*\n\n"
                f"*{ao.titre[:100]}*\n"
                f"Réf. {ao.reference}\n\n"
                f"📅 Clôture : {ao.date_cloture.strftime('%d/%m/%Y') if ao.date_cloture else 'N/A'}\n\n"
                f"🔗 https://gov.netsync.bf/ao/{ao.id}"
            )
        else:
            secteur_emoji = {
                "informatique": "💻", "btp": "🏗️", "sante": "🏥",
                "agriculture": "🌾", "conseil": "📋", "equipement": "⚙️",
                "energie": "⚡", "education": "🎓", "autre": "📄",
            }.get(ao.secteur, "📄")
            urgent = f"\n⚡ *Seulement {ao.jours_restants} jours restants !*" if ao.est_urgent else ""
            return (
                f"🔔 *Nouveau AO — {ao.secteur.upper()}* {secteur_emoji}\n\n"
                f"*{ao.titre[:120]}*\n\n"
                f"🏛️ {ao.autorite_contractante or 'N/A'}\n"
                f"📋 Réf. _{ao.reference}_\n"
                f"📅 Clôture : {ao.date_cloture.strftime('%d/%m/%Y') if ao.date_cloture else 'Non précisée'}"
                f"{urgent}\n\n"
                f"📥 https://gov.netsync.bf/ao/{ao.id}\n\n"
                f"_NetSync Gov — Appels d'offres BF_"
            )




class AlertEngine:
    """
    Moteur principal d'alertes.

    Pour chaque nouveau AO :
    1. Trouve les abonnés dont les préférences correspondent (secteur, mots-clés, source).
    2. Vérifie que l'alerte n'a pas déjà été envoyée (déduplication).
    3. Envoie via email et/ou WhatsApp selon la préférence de l'abonné.
    4. Logue le résultat dans envois_alertes.
    """

    def __init__(self, db: Session):
        self.db = db
        self.email_sender = EmailSender()
        self.wa_sender = WhatsAppSender()
        self._stats = {"envoyes": 0, "echecs": 0, "ignores": 0}

    def process_new_ao(self, ao: AppelOffre) -> int:
        """
        Traite un nouvel AO et envoie les alertes pertinentes.

        Returns:
            Nombre d'alertes envoyées.
        """
        abonnes_a_alerter = self._find_matching_abonnes(ao)
        logger.info(f"AO {ao.reference} : {len(abonnes_a_alerter)} abonné(s) à alerter")

        sent = 0
        for abonne, prefs in abonnes_a_alerter:
            sent += self._send_alert(ao, abonne, prefs, "nouveau_ao")

        return sent

    def process_rappels_j3(self) -> int:
        """
        Envoie les rappels J-3 pour les AO qui clôturent dans 3 jours.
        À appeler quotidiennement.
        """
        target_date = date.today() + timedelta(days=3)
        ao_urgents = (
            self.db.query(AppelOffre)
            .filter(
                AppelOffre.date_cloture == target_date,
                AppelOffre.statut == "ouvert",
            )
            .all()
        )

        logger.info(f"Rappels J-3 : {len(ao_urgents)} AO clôturent le {target_date}")
        total_sent = 0

        for ao in ao_urgents:
            abonnes = self._find_matching_abonnes(ao)
            for abonne, prefs in abonnes:
                if prefs.rappel_j3:
                    total_sent += self._send_alert(ao, abonne, prefs, "rappel_j3")

        return total_sent

    def _find_matching_abonnes(self, ao: AppelOffre) -> list:
        """
        Cherche les abonnés Pro/Équipe dont les préférences correspondent à l'AO.
        Utilise une requête SQL optimisée avec index GIN sur secteurs[].
        """
        results = self.db.execute(
            text("""
                SELECT a.id, a.email, a.whatsapp, a.prenom, a.nom,
                       p.id as pref_id, p.secteurs, p.mots_cles,
                       p.sources, p.canal, p.rappel_j3
                FROM abonnes a
                JOIN preferences_alertes p ON p.abonne_id = a.id
                WHERE a.plan != 'gratuit'
                  AND a.actif = true
                  AND p.actif = true
                  AND (
                    :secteur = ANY(p.secteurs)
                    OR array_length(p.secteurs, 1) IS NULL
                  )
                  AND (
                    p.sources = '{}'::varchar[]
                    OR :source = ANY(p.sources)
                    OR array_length(p.sources, 1) IS NULL
                  )
                  AND NOT EXISTS (
                    SELECT 1 FROM envois_alertes e
                    WHERE e.abonne_id = a.id
                      AND e.ao_id = :ao_id
                      AND e.type_alerte = 'nouveau_ao'
                  )
            """),
            {"secteur": ao.secteur, "source": ao.source, "ao_id": str(ao.id)},
        ).fetchall()

        # Reconstruire objets Abonne + PreferenceAlerte
        abonnes_prefs = []
        for row in results:
            abonne = self.db.get(Abonne, row.id)
            prefs = self.db.get(PreferenceAlerte, row.pref_id)
            if abonne and prefs:
                # Vérifier mots-clés si secteur ne match pas directement
                if ao.secteur not in (prefs.secteurs or []):
                    if not self._check_mots_cles(ao, prefs.mots_cles or []):
                        continue
                abonnes_prefs.append((abonne, prefs))

        return abonnes_prefs

    def _check_mots_cles(self, ao: AppelOffre, mots_cles: list) -> bool:
        """Vérifie si des mots-clés correspondent au titre/description de l'AO."""
        if not mots_cles:
            return True  # Pas de filtre = tout passe
        texte = f"{ao.titre} {ao.description or ''}".lower()
        return any(kw.lower() in texte for kw in mots_cles)

    def _send_alert(
        self, ao: AppelOffre, abonne: Abonne,
        prefs: PreferenceAlerte, type_alerte: str
    ) -> int:
        """Envoie l'alerte sur le(s) canal(aux) configuré(s)."""
        sent = 0
        canal = prefs.canal or "les_deux"

        if canal in ("email", "les_deux") and abonne.email:
            ok = self._send_email_alert(ao, abonne, type_alerte)
            if ok:
                sent += 1
                self._log_envoi(ao, abonne, "email", type_alerte, "envoye")
            else:
                self._log_envoi(ao, abonne, "email", type_alerte, "echec")

        if canal in ("whatsapp", "les_deux") and abonne.whatsapp:
            ok = self.wa_sender.send(abonne.whatsapp, ao, type_alerte)
            if ok:
                sent += 1
                self._log_envoi(ao, abonne, "whatsapp", type_alerte, "envoye")
            else:
                self._log_envoi(ao, abonne, "whatsapp", type_alerte, "echec")

        return sent

    def _send_email_alert(self, ao: AppelOffre, abonne: Abonne, type_alerte: str) -> bool:
        """Envoie l'alerte email."""
        subject, html = self.email_sender.render_ao_alert(ao, abonne)
        if type_alerte == "rappel_j3":
            subject = f"[NetSync Gov] ⏰ Rappel clôture J-{ao.jours_restants} — {ao.titre[:50]}"
        return self.email_sender.send(abonne.email, subject, html)

    def _log_envoi(
        self, ao: AppelOffre, abonne: Abonne,
        canal: str, type_alerte: str, statut: str,
        erreur: Optional[str] = None
    ) -> None:
        """Logue l'envoi dans la table envois_alertes."""
        try:
            log = EnvoiAlerte(
                abonne_id=abonne.id,
                ao_id=ao.id,
                canal=canal,
                statut=statut,
                type_alerte=type_alerte,
                erreur=erreur,
                tentatives=1,
            )
            self.db.add(log)
            self.db.flush()
            if statut == "envoye":
                self._stats["envoyes"] += 1
            else:
                self._stats["echecs"] += 1
        except Exception as e:
            logger.error(f"Erreur log envoi : {e}")

    def get_stats(self) -> dict:
        return dict(self._stats)
