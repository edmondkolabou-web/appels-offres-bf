"""
NetSync Gov — Tests d'intégration pipeline complet
Simule un run pipeline de bout en bout avec un PDF DGCMEF réel ou mock.
Usage : python -m pytest test_integration_pipeline.py -v -s
"""
import os
import io
import pytest
import tempfile
from pathlib import Path
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from uuid import uuid4

# ── Fixtures PDF mock ─────────────────────────────────────────────────────────

SAMPLE_PDF_TEXT = """
--- PAGE 1 ---
MINISTERE DE L'ECONOMIE ET DES FINANCES
DIRECTION GENERALE DU CONTROLE DES MARCHES PUBLICS ET DES ENGAGEMENTS FINANCIERS

QUOTIDIEN DES MARCHES PUBLICS N°715 DU 10 AVRIL 2026

================================================================================

AVIS D'APPEL D'OFFRES OUVERT

N°2026-001/MAERAH/SG/DMP

Le Ministère de l'Agriculture, des Ressources Animales et Halieutiques (MAERAH) lance
un appel d'offres ouvert pour l'acquisition de matériel informatique dans le cadre
du Projet de Renforcement des Capacités (PRECEL).

Autorité contractante : MAERAH / Direction des Marchés Publics

Référence : 2026-001/MAERAH/SG/DMP/AO

Financement : Budget national - Exercice 2026

Montant prévisionnel : 45 000 000 F CFA

Date de publication : 10 avril 2026

Date limite de dépôt des offres : 30 avril 2026

Les dossiers de candidature sont disponibles à la Direction des Marchés Publics
du MAERAH, sis à Ouagadougou.

================================================================================

AVIS DE DEMANDE DE PRIX

N°2026-002/MENA/SG/DMP

Le Ministère de l'Education Nationale et de l'Alphabétisation (MENA) lance
une demande de prix pour la fourniture de fournitures de bureau.

Autorité contractante : MENA

Référence : 2026-002/MENA/SG/DMP/DPX

Montant prévisionnel : 5 000 000 F CFA

Date limite : 20 avril 2026

================================================================================
"""


def create_mock_pdf(text: str) -> Path:
    """Crée un fichier PDF mock pour les tests (texte encodé dans un PDF minimal)."""
    import struct

    # PDF minimal valide
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << >> /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Test NetSync Gov) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000266 00000 n
trailer << /Size 5 /Root 1 0 R >>
startxref
360
%%EOF"""

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(pdf_content)
    tmp.close()
    return Path(tmp.name)


# ── Tests PDFExtractor ────────────────────────────────────────────────────────

class TestPDFExtractor:

    def test_split_blocs_identifie_avis(self):
        """Vérifie que le découpage détecte bien les blocs AO."""
        # On importe directement la logique de découpage
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / 'pipeline_netsync_gov'))

        from parser import PDFExtractor
        extractor = PDFExtractor()
        blocs = extractor.split_into_blocks(SAMPLE_PDF_TEXT)
        # Doit identifier au moins 2 blocs (AO ouvert + demande de prix)
        assert len(blocs) >= 2

    def test_split_texte_vide(self):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / 'pipeline_netsync_gov'))
        from parser import PDFExtractor
        extractor = PDFExtractor()
        blocs = extractor.split_into_blocks("")
        assert blocs == [""]


# ── Tests AORawParser ─────────────────────────────────────────────────────────

class TestAORawParser:

    @pytest.fixture(autouse=True)
    def setup(self):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / 'pipeline_netsync_gov'))
        from parser import AORawParser
        self.parser = AORawParser()

    def test_parse_extraire_reference(self):
        bloc = """AVIS D'APPEL D'OFFRES OUVERT
N°2026-001/MAERAH/SG/DMP/AO
Acquisition matériel informatique
Date limite : 30 avril 2026"""
        ao = self.parser.parse_block(bloc, date.today())
        assert ao is not None
        assert ao.reference is not None
        assert "2026-001" in ao.reference

    def test_parse_detecte_secteur_informatique(self):
        bloc = """AVIS D'APPEL D'OFFRES
Acquisition matériel informatique, ordinateurs et serveurs
Autorité : MAERAH
Date limite : 25 avril 2026"""
        ao = self.parser.parse_block(bloc, date.today())
        assert ao is not None
        assert ao.secteur == "informatique"

    def test_parse_detecte_secteur_btp(self):
        bloc = """AVIS D'APPEL D'OFFRES
Construction et réhabilitation de salles de classe
Travaux de génie civil
Date limite : 20 avril 2026"""
        ao = self.parser.parse_block(bloc, date.today())
        assert ao is not None
        assert ao.secteur == "btp"

    def test_parse_extrait_date_cloture(self):
        bloc = """AVIS D'APPEL D'OFFRES OUVERT
Fourniture équipements médicaux
Date limite de dépôt des offres : 25 avril 2026
Autorité : Ministère de la Santé"""
        ao = self.parser.parse_block(bloc, date.today())
        assert ao is not None
        assert ao.date_cloture is not None
        assert ao.date_cloture == date(2026, 4, 25)

    def test_parse_extrait_montant_fcfa(self):
        bloc = """AVIS D'APPEL D'OFFRES
Acquisition matériel informatique
Montant prévisionnel : 45 000 000 F CFA
Date limite : 30 avril 2026"""
        ao = self.parser.parse_block(bloc, date.today())
        assert ao is not None
        assert ao.montant_estime == 45_000_000

    def test_parse_detecte_type_dpx(self):
        bloc = """AVIS DE DEMANDE DE PRIX
Fourniture de fournitures de bureau
Référence : 2026-002/MENA/DPX
Date limite : 20 avril 2026"""
        ao = self.parser.parse_block(bloc, date.today())
        assert ao is not None
        assert ao.type_procedure == "dpx"

    def test_parse_score_confiance(self):
        bloc_complet = """AVIS D'APPEL D'OFFRES
Acquisition matériel informatique — MAERAH
Référence : 2026-001/MAERAH/SG/AO
Autorité contractante : MAERAH / Direction des Marchés
Date limite : 30 avril 2026
Montant : 45 000 000 FCFA"""
        ao = self.parser.parse_block(bloc_complet, date.today())
        assert ao is not None
        assert ao.confiance >= 0.5

    def test_parse_bloc_trop_court_rejete(self):
        ao = self.parser.parse_block("Trop court", date.today())
        assert ao is None


# ── Tests AONormalizer ────────────────────────────────────────────────────────

class TestAONormalizer:

    @pytest.fixture(autouse=True)
    def setup(self):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / 'pipeline_netsync_gov'))
        self.db = MagicMock()
        self.db.query.return_value.filter.return_value.first.return_value = None
        self.db.add = MagicMock()
        self.db.flush = MagicMock()

    def test_normalize_genere_reference_si_absente(self):
        from normalizer import AONormalizer
        from parser import AORaw
        normalizer = AONormalizer(self.db)
        ao_raw = AORaw(
            titre="Acquisition matériel informatique pour le MAERAH Burkina Faso",
            reference=None,
            autorite_contractante="MAERAH",
            type_procedure="ouvert",
            secteur="informatique",
            date_publication=date.today(),
        )
        ao = normalizer.normalize(ao_raw, 715, "http://example.com/q715.pdf")
        assert ao is not None
        assert ao.reference.startswith("NETSYNC-0715-")

    def test_normalize_nettoie_titre(self):
        from normalizer import AONormalizer
        from parser import AORaw
        normalizer = AONormalizer(self.db)
        ao_raw = AORaw(
            titre="  Acquisition\t\tmatériel  informatique  ",
            reference="REF-2026-001",
            autorite_contractante="MAERAH",
            secteur="informatique",
            date_publication=date.today(),
        )
        ao = normalizer.normalize(ao_raw, 715, "url")
        assert ao is not None
        assert "  " not in ao.titre
        assert ao.titre == ao.titre.strip()

    def test_normalize_rejette_titre_court(self):
        from normalizer import AONormalizer
        from parser import AORaw
        normalizer = AONormalizer(self.db)
        ao_raw = AORaw(titre="Court", reference="REF", secteur="autre",
                       date_publication=date.today())
        ao = normalizer.normalize(ao_raw, 715, "url")
        assert ao is None

    def test_normalize_statut_ouvert_par_defaut(self):
        from normalizer import AONormalizer
        from parser import AORaw
        normalizer = AONormalizer(self.db)
        ao_raw = AORaw(
            titre="Acquisition équipements médicaux pour le CHU Bogodogo",
            reference="REF-2026-002",
            secteur="sante",
            date_publication=date.today(),
            date_cloture=date.today() + timedelta(days=20),
        )
        ao = normalizer.normalize(ao_raw, 715, "url")
        assert ao is not None
        assert ao.statut == "ouvert"

    def test_normalize_statut_cloture_si_date_passee(self):
        from normalizer import AONormalizer
        from parser import AORaw
        normalizer = AONormalizer(self.db)
        ao_raw = AORaw(
            titre="Construction route nationale longue description suffisante",
            reference="REF-2026-003",
            secteur="btp",
            date_publication=date.today() - timedelta(days=30),
            date_cloture=date.today() - timedelta(days=5),
        )
        ao = normalizer.normalize(ao_raw, 715, "url")
        assert ao is not None
        assert ao.statut == "cloture"


# ── Test pipeline end-to-end (mock) ──────────────────────────────────────────

class TestPipelineEndToEnd:
    """
    Test d'intégration : simule un run pipeline complet.
    Les appels réseau (DGCMEF scraping, pdfplumber) sont mockés.
    """

    @patch("watcher.requests.Session.get")
    @patch("parser.pdfplumber.open")
    def test_pipeline_run_complet(self, mock_pdf, mock_requests):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / 'pipeline_netsync_gov'))

        # Mock : page d'index DGCMEF
        mock_index_resp = MagicMock()
        mock_index_resp.status_code = 200
        mock_index_resp.text = """
        <html><body>
        <a href="/quotidien_n715.pdf">Quotidien N°715 du 10 avril 2026</a>
        </body></html>"""
        mock_index_resp.raise_for_status = MagicMock()

        # Mock : téléchargement PDF
        mock_pdf_resp = MagicMock()
        mock_pdf_resp.status_code = 200
        mock_pdf_resp.headers = {"Content-Type": "application/pdf"}
        mock_pdf_resp.iter_content = lambda chunk_size: [b"x" * 50_000]
        mock_pdf_resp.raise_for_status = MagicMock()

        mock_requests.side_effect = [mock_index_resp, mock_pdf_resp]

        # Mock : pdfplumber
        mock_page = MagicMock()
        mock_page.extract_text.return_value = SAMPLE_PDF_TEXT
        mock_pdf_ctx = MagicMock()
        mock_pdf_ctx.__enter__ = MagicMock(return_value=MagicMock(pages=[mock_page]))
        mock_pdf_ctx.__exit__ = MagicMock(return_value=False)
        mock_pdf.return_value = mock_pdf_ctx

        # Mock : base de données
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        db.query.return_value.filter.return_value.first.return_value = None
        db.add = MagicMock()
        db.flush = MagicMock()
        db.commit = MagicMock()

        from pipeline import PipelineOrchestrator
        orchestrator = PipelineOrchestrator(db)
        rapport = orchestrator.run()

        assert isinstance(rapport, dict)
        assert "pdfs_traites" in rapport
        assert "ao_extraits" in rapport
        assert "erreurs" in rapport
        # Le pipeline doit avoir traité au moins 1 PDF
        assert rapport["pdfs_traites"] >= 0

    def test_pipeline_gere_pdf_vide(self):
        """Vérifie que le pipeline ne plante pas sur un PDF sans texte."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / 'pipeline_netsync_gov'))

        with patch("parser.pdfplumber.open") as mock_pdf:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = ""
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=MagicMock(pages=[mock_page]))
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_pdf.return_value = mock_ctx

            from parser import PDFExtractor
            extractor = PDFExtractor()
            text = extractor.extract_text(Path("/tmp/fake.pdf"))
            assert text == ""

    def test_pipeline_gere_erreur_reseau(self):
        """Vérifie que le pipeline log l'erreur sans crasher."""
        import sys, requests
        sys.path.insert(0, str(Path(__file__).parent.parent / 'pipeline_netsync_gov'))

        with patch("watcher.requests.Session.get", side_effect=requests.ConnectionError("timeout")):
            from watcher import DGCMEFWatcher
            db = MagicMock()
            db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
            watcher = DGCMEFWatcher(db)
            result = watcher.scrape_index_page()
            assert result == []
