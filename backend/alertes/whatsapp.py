"""
NetSync Gov — Module WhatsApp Business API (Meta Cloud API v18)
Gestion complète : envoi, templates, retry, logs, validation numéros BF.
"""
import re
import os
import logging
from typing import Optional
from datetime import date

import requests
from sqlalchemy.orm import Session

from models import AppelOffre, Abonne, EnvoiAlerte

logger = logging.getLogger("netsync.whatsapp")

PHONE_ID   = os.getenv("WHATSAPP_PHONE_ID", "")
API_TOKEN  = os.getenv("WHATSAPP_API_TOKEN", "")
API_URL    = f"https://graph.facebook.com/v18.0/{PHONE_ID}/messages"
WABA_ID    = os.getenv("WHATSAPP_WABA_ID", "")

# Noms des templates pré-approuvés Meta (à créer dans le Business Manager)
TEMPLATE_NOUVEL_AO  = "netsync_nouvel_ao"
TEMPLATE_RAPPEL_J3  = "netsync_rappel_cloture"
TEMPLATE_BIENVENUE  = "netsync_bienvenue"

SECTEUR_EMOJI = {
    "informatique": "💻", "btp": "🏗️", "sante": "🏥",
    "agriculture": "🌾", "conseil": "📋", "equipement": "⚙️",
    "energie": "⚡", "education": "🎓", "transport": "🚛",
    "autre": "📄",
}


def normalize_phone(raw: str) -> Optional[str]:
    """
    Normalise un numéro de téléphone pour l'API WhatsApp.
    Format attendu : chaîne de chiffres sans + ni espaces, avec préfixe pays.
    Ex: "+226 70 12 34 56" → "22670123456"
    """
    if not raw:
        return None
    digits = re.sub(r"[^\d]", "", raw)
    # Numéros burkinabè : 8 chiffres locaux → ajouter 226
    if len(digits) == 8:
        digits = "226" + digits
    # Commençant par 0 : supprimer le 0 et ajouter l'indicatif
    elif len(digits) == 9 and digits.startswith("0"):
        digits = "226" + digits[1:]
    # Vérification finale
    if len(digits) < 10 or len(digits) > 15:
        logger.warning(f"Numéro invalide ignoré : {raw!r} → {digits!r}")
        return None
    return digits


class WhatsAppClient:
    """
    Client WhatsApp Business API (Meta Cloud API).

    Deux modes d'envoi :
    1. Template message — requis pour initier une conversation (hors fenêtre 24h)
    2. Text message — disponible uniquement dans la fenêtre 24h post-réponse utilisateur
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json",
        })

    # ── Envoi message texte libre (fenêtre 24h) ─────────────────────────────

    def send_text(self, to: str, body: str) -> dict:
        """
        Envoie un message texte libre.
        Uniquement valide si l'utilisateur a écrit dans les 24 dernières heures.
        """
        phone = normalize_phone(to)
        if not phone:
            return {"success": False, "error": "Numéro invalide"}

        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": body, "preview_url": False},
        }
        return self._post(payload)

    # ── Envoi via template approuvé ──────────────────────────────────────────

    def send_template(self, to: str, template_name: str,
                      language: str = "fr", components: list = None) -> dict:
        """
        Envoie un message via un template pré-approuvé Meta.
        C'est le seul moyen d'initier une conversation après la fenêtre 24h.

        Args:
            to: Numéro de téléphone (tout format BF accepté)
            template_name: Nom du template dans le Business Manager Meta
            language: Code langue du template (fr = Français)
            components: Variables du template sous forme de components Meta
        """
        phone = normalize_phone(to)
        if not phone:
            return {"success": False, "error": "Numéro invalide"}

        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
            },
        }
        if components:
            payload["template"]["components"] = components

        return self._post(payload)

    def _post(self, payload: dict) -> dict:
        """Envoie la requête et retourne un dict normalisé."""
        if not API_TOKEN or not PHONE_ID:
            # Mode simulation (dev/test)
            logger.info(f"[SIMULATION WA] → {payload.get('to')} | {payload.get('type')}")
            return {"success": True, "simulated": True, "message_id": "sim_0"}

        try:
            resp = self.session.post(API_URL, json=payload, timeout=15)
            data = resp.json()
            if resp.status_code == 200:
                msg_id = data.get("messages", [{}])[0].get("id", "")
                logger.info(f"WA envoyé → {payload.get('to')} | id={msg_id}")
                return {"success": True, "message_id": msg_id}
            else:
                err = data.get("error", {})
                logger.error(f"WA erreur {resp.status_code} → {payload.get('to')}: {err}")
                return {"success": False, "error": err.get("message", "Erreur inconnue"),
                        "code": err.get("code")}
        except requests.Timeout:
            logger.error(f"WA timeout → {payload.get('to')}")
            return {"success": False, "error": "Timeout API WhatsApp"}
        except requests.RequestException as e:
            logger.error(f"WA exception → {payload.get('to')}: {e}")
            return {"success": False, "error": str(e)}


class AOAlertWhatsApp:
    """
    Construit et envoie les alertes WhatsApp pour les AOs.
    Utilise les templates Meta en priorité, text message en fallback.
    """

    def __init__(self):
        self.client = WhatsAppClient()

    def send_nouvel_ao(self, abonne: Abonne, ao: AppelOffre) -> dict:
        """
        Alerte : nouveau appel d'offres correspondant aux préférences.

        Template Meta : netsync_nouvel_ao
        Variables :
          {{1}} = Prénom de l'abonné
          {{2}} = Titre de l'AO (tronqué à 100 chars)
          {{3}} = Autorité contractante
          {{4}} = Secteur
          {{5}} = Date de clôture (ou "Non précisée")
          {{6}} = URL de détail
        """
        cloture = ao.date_cloture.strftime("%d/%m/%Y") if ao.date_cloture else "Non précisée"
        detail_url = f"https://gov.netsync.bf/aos/{ao.id}"
        emoji = SECTEUR_EMOJI.get(ao.secteur, "📄")

        components = [
            {
                "type": "header",
                "parameters": [{"type": "text", "text": f"{emoji} Nouveau AO — {ao.secteur.upper()}"}]
            },
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": abonne.prenom},
                    {"type": "text", "text": ao.titre[:100]},
                    {"type": "text", "text": ao.autorite_contractante or "N/A"},
                    {"type": "text", "text": ao.secteur.title()},
                    {"type": "text", "text": cloture},
                    {"type": "text", "text": detail_url},
                ]
            },
            {
                "type": "button",
                "sub_type": "url",
                "index": "0",
                "parameters": [{"type": "text", "text": str(ao.id)}]
            }
        ]

        result = self.client.send_template(
            to=abonne.whatsapp,
            template_name=TEMPLATE_NOUVEL_AO,
            components=components,
        )

        # Fallback text si template échoue (ex: template non encore approuvé)
        if not result["success"] and result.get("code") in (132000, 132001):
            logger.warning("Template non approuvé — fallback message texte")
            body = self._format_text_nouvel_ao(abonne, ao)
            result = self.client.send_text(abonne.whatsapp, body)
            result["fallback"] = True

        return result

    def send_rappel_j3(self, abonne: Abonne, ao: AppelOffre) -> dict:
        """
        Rappel : clôture dans 3 jours.

        Template Meta : netsync_rappel_cloture
        Variables :
          {{1}} = Prénom
          {{2}} = Titre AO (tronqué)
          {{3}} = Jours restants (ex: "3")
          {{4}} = Date de clôture formatée
          {{5}} = URL de détail
        """
        jours = ao.jours_restants or 3
        cloture = ao.date_cloture.strftime("%d/%m/%Y") if ao.date_cloture else "—"
        detail_url = f"https://gov.netsync.bf/aos/{ao.id}"

        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": abonne.prenom},
                    {"type": "text", "text": ao.titre[:100]},
                    {"type": "text", "text": str(jours)},
                    {"type": "text", "text": cloture},
                    {"type": "text", "text": detail_url},
                ]
            }
        ]

        result = self.client.send_template(
            to=abonne.whatsapp,
            template_name=TEMPLATE_RAPPEL_J3,
            components=components,
        )

        if not result["success"]:
            body = (
                f"⏰ *Rappel NetSync Gov* — Clôture dans {jours} jour(s)\n\n"
                f"*{ao.titre[:100]}*\n"
                f"Réf. {ao.reference}\n\n"
                f"📅 Date limite : {cloture}\n"
                f"🔗 {detail_url}"
            )
            result = self.client.send_text(abonne.whatsapp, body)
            result["fallback"] = True

        return result

    def send_bienvenue(self, abonne: Abonne) -> dict:
        """
        Message de bienvenue après inscription.
        Confirme l'activation des alertes WhatsApp.
        """
        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": abonne.prenom},
                    {"type": "text", "text": "07h00"},
                ]
            }
        ]
        return self.client.send_template(
            to=abonne.whatsapp,
            template_name=TEMPLATE_BIENVENUE,
            components=components,
        )

    def _format_text_nouvel_ao(self, abonne: Abonne, ao: AppelOffre) -> str:
        """Message texte de fallback (fenêtre 24h uniquement)."""
        emoji = SECTEUR_EMOJI.get(ao.secteur, "📄")
        cloture = ao.date_cloture.strftime("%d/%m/%Y") if ao.date_cloture else "Non précisée"
        urgent_line = f"\n⚡ *Seulement {ao.jours_restants} jours restants !*" if ao.est_urgent else ""
        return (
            f"🔔 *Nouveau AO — {ao.secteur.upper()}* {emoji}\n\n"
            f"Bonjour {abonne.prenom},\n\n"
            f"*{ao.titre[:120]}*\n\n"
            f"🏛️ {ao.autorite_contractante or 'N/A'}\n"
            f"📋 Réf. _{ao.reference}_\n"
            f"📅 Clôture : {cloture}"
            f"{urgent_line}\n\n"
            f"🔗 https://gov.netsync.bf/aos/{ao.id}\n\n"
            f"_NetSync Gov — Appels d'offres Burkina Faso_"
        )
