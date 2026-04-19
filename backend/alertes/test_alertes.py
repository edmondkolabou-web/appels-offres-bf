"""
NetSync Gov — Tests unitaires du système d'alertes
Couvre : normalisation numéros, templates email, matching abonnés, retry.
Usage : python -m pytest test_alertes.py -v
"""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

from whatsapp import normalize_phone, WhatsAppClient, AOAlertWhatsApp
from email_templates import render_nouvel_ao, render_rappel_j3, render_bienvenue
from email_sender import ResendClient
from composables_alerts import build_ao_email_context


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_ao(**kwargs):
    ao = MagicMock()
    ao.id             = uuid4()
    ao.reference      = "2026-001/MENA/SG/DMP"
    ao.titre          = "Acquisition matériel informatique — Ministère de l'Éducation"
    ao.description    = "Fourniture et installation d'ordinateurs et imprimantes"
    ao.autorite_contractante = "MENA / Ministère de l'Éducation"
    ao.type_procedure = "ouvert"
    ao.secteur        = "informatique"
    ao.statut         = "ouvert"
    ao.source         = "dgcmef"
    ao.date_publication = date.today()
    ao.date_cloture   = date.today() + timedelta(days=10)
    ao.montant_estime = 45_000_000
    ao.est_urgent     = False
    ao.jours_restants = 10
    for k, v in kwargs.items():
        setattr(ao, k, v)
    return ao


def make_abonne(**kwargs):
    ab = MagicMock()
    ab.id       = uuid4()
    ab.prenom   = "Adama"
    ab.nom      = "Kabore"
    ab.email    = "adama@entreprise.bf"
    ab.whatsapp = "+226 70 12 34 56"
    ab.plan     = "pro"
    for k, v in kwargs.items():
        setattr(ab, k, v)
    return ab


# ── Tests normalisation numéros ───────────────────────────────────────────────

class TestNormalizePhone:

    def test_format_complet(self):
        assert normalize_phone("+226 70 12 34 56") == "22670123456"

    def test_format_8_chiffres(self):
        assert normalize_phone("70123456") == "22670123456"

    def test_format_avec_espaces(self):
        assert normalize_phone("226 70 12 34 56") == "22670123456"

    def test_format_international(self):
        assert normalize_phone("+33 6 12 34 56 78") == "33612345678"

    def test_numero_vide(self):
        assert normalize_phone("") is None
        assert normalize_phone(None) is None

    def test_numero_trop_court(self):
        assert normalize_phone("1234") is None

    def test_0_prefix_local(self):
        # 070123456 → supprimer le 0 → 70123456 → ajouter 226
        assert normalize_phone("070123456") == "22670123456"


# ── Tests templates email ─────────────────────────────────────────────────────

class TestEmailTemplates:

    def test_nouvel_ao_subject_contient_secteur(self):
        subject, html = render_nouvel_ao(
            prenom="Adama", ao_titre="Acquisition matériel IT", ao_reference="REF-001",
            autorite="MENA", type_procedure="ouvert", secteur="informatique",
            date_publication="15 avr. 2026", date_cloture="25 avr. 2026",
            montant="45 M FCFA", source="dgcmef",
            ao_url="https://gov.netsync.bf/aos/123",
        )
        assert "INFORMATIQUE" in subject
        assert "Acquisition matériel IT" in subject

    def test_nouvel_ao_html_contient_cta(self):
        _, html = render_nouvel_ao(
            prenom="Adama", ao_titre="Test AO", ao_reference="REF-001",
            autorite="MENA", type_procedure="ouvert", secteur="btp",
            date_publication="15 avr. 2026", date_cloture=None,
            montant=None, source="dgcmef",
            ao_url="https://gov.netsync.bf/aos/123",
        )
        assert "Voir le détail" in html
        assert "cta-btn" in html
        assert "gov.netsync.bf" in html

    def test_urgent_affiche_banner(self):
        _, html = render_nouvel_ao(
            prenom="Adama", ao_titre="AO Urgent", ao_reference="REF-001",
            autorite="MENA", type_procedure="ouvert", secteur="informatique",
            date_publication="15 avr. 2026", date_cloture="18 avr. 2026",
            montant=None, source="dgcmef",
            ao_url="https://gov.netsync.bf/aos/123",
            est_urgent=True, jours_restants=3,
        )
        assert "urgent-banner" in html
        assert "3 jour" in html

    def test_rappel_j3_subject_contient_jours(self):
        subject, html = render_rappel_j3(
            prenom="Edmond", ao_titre="AO Test", ao_reference="REF-002",
            autorite="MAERAH", date_cloture="18 avr. 2026",
            jours_restants=2, ao_url="https://gov.netsync.bf/aos/456",
        )
        assert "J-2" in subject
        assert "2 jour" in html

    def test_bienvenue_contient_plan(self):
        subject, html = render_bienvenue(
            prenom="Adama", plan="pro", secteurs=["informatique", "btp"]
        )
        assert "Plan Pro" in html
        assert "informatique, btp" in html
        assert "07h00" in html

    def test_html_valide_structure(self):
        _, html = render_nouvel_ao(
            prenom="Test", ao_titre="Test", ao_reference="REF",
            autorite="Auth", type_procedure="ouvert", secteur="autre",
            date_publication="15 avr. 2026", date_cloture=None,
            montant=None, source="dgcmef",
            ao_url="https://gov.netsync.bf/aos/1",
        )
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html
        assert html.count("<html") == 1
        assert html.count("</html>") == 1


# ── Tests build_ao_email_context ──────────────────────────────────────────────

class TestBuildContext:

    def test_montant_formate_millions(self):
        ao = make_ao(montant_estime=45_000_000)
        ctx = build_ao_email_context(ao)
        assert ctx["montant"] == "45 M FCFA"

    def test_montant_formate_milliards(self):
        ao = make_ao(montant_estime=2_500_000_000)
        ctx = build_ao_email_context(ao)
        assert "Mrd" in ctx["montant"]

    def test_montant_none(self):
        ao = make_ao(montant_estime=None)
        ctx = build_ao_email_context(ao)
        assert ctx["montant"] is None

    def test_date_formatee(self):
        ao = make_ao(date_publication=date(2026, 4, 15))
        ctx = build_ao_email_context(ao)
        assert "avr." in ctx["date_publication"]
        assert "2026" in ctx["date_publication"]


# ── Tests ResendClient (mock) ─────────────────────────────────────────────────

class TestResendClient:

    @patch("email_sender.RESEND_API_KEY", "")
    def test_simulation_si_pas_de_cle(self):
        client = ResendClient()
        result = client.send("test@test.bf", "Sujet", "<p>Test</p>")
        assert result["success"] is True
        assert result.get("simulated") is True

    @patch("email_sender.RESEND_API_KEY", "re_test_key")
    @patch("email_sender.requests.Session.post")
    def test_envoi_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "email_abc123"}
        mock_post.return_value = mock_resp
        client = ResendClient()
        result = client.send("test@test.bf", "Sujet", "<p>Test</p>")
        assert result["success"] is True
        assert result["email_id"] == "email_abc123"

    @patch("email_sender.RESEND_API_KEY", "re_test_key")
    @patch("email_sender.requests.Session.post")
    def test_envoi_erreur_404(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"message": "Not found"}
        mock_post.return_value = mock_resp
        client = ResendClient()
        result = client.send("test@test.bf", "Sujet", "<p>Test</p>")
        assert result["success"] is False


# ── Tests WhatsAppClient (mock) ───────────────────────────────────────────────

class TestWhatsAppClient:

    @patch("whatsapp.API_TOKEN", "")
    @patch("whatsapp.PHONE_ID", "")
    def test_simulation_si_pas_de_token(self):
        client = WhatsAppClient()
        result = client.send_text("+226 70 00 00 00", "Test message")
        assert result["success"] is True
        assert result.get("simulated") is True

    @patch("whatsapp.API_TOKEN", "test_token")
    @patch("whatsapp.PHONE_ID", "123456789")
    @patch("whatsapp.requests.Session.post")
    def test_envoi_template_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"messages": [{"id": "wamid.123"}]}
        mock_post.return_value = mock_resp
        client = WhatsAppClient()
        result = client.send_template("+226 70 12 34 56", "test_template")
        assert result["success"] is True
        assert result["message_id"] == "wamid.123"

    def test_numero_invalide_rejete(self):
        client = WhatsAppClient()
        result = client.send_text("123", "Test")
        assert result["success"] is False
        assert "invalide" in result["error"].lower()


# ── Tests AOAlertWhatsApp ─────────────────────────────────────────────────────

class TestAOAlertWhatsApp:

    @patch("whatsapp.API_TOKEN", "")
    @patch("whatsapp.PHONE_ID", "")
    def test_nouvel_ao_simulation(self):
        ao     = make_ao()
        abonne = make_abonne()
        wa     = AOAlertWhatsApp()
        result = wa.send_nouvel_ao(abonne, ao)
        assert result["success"] is True

    @patch("whatsapp.API_TOKEN", "")
    @patch("whatsapp.PHONE_ID", "")
    def test_rappel_j3_simulation(self):
        ao     = make_ao(date_cloture=date.today() + timedelta(days=3),
                         est_urgent=True, jours_restants=3)
        abonne = make_abonne()
        wa     = AOAlertWhatsApp()
        result = wa.send_rappel_j3(abonne, ao)
        assert result["success"] is True

    @patch("whatsapp.API_TOKEN", "")
    @patch("whatsapp.PHONE_ID", "")
    def test_abonne_sans_whatsapp(self):
        ao     = make_ao()
        abonne = make_abonne(whatsapp=None)
        wa     = AOAlertWhatsApp()
        result = wa.send_nouvel_ao(abonne, ao)
        # normalize_phone(None) → None → échec attendu
        assert result["success"] is False
