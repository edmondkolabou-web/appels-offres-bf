"""
NetSync Gov Candidature — Tests unitaires et d'intégration
Usage : python -m pytest 07_tests_candidatures.py -v
"""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_ao(type_procedure="ouvert", **kwargs):
    ao = MagicMock()
    ao.id                    = uuid4()
    ao.titre                 = "Acquisition matériel informatique — MAERAH"
    ao.type_procedure        = type_procedure
    ao.secteur               = "informatique"
    ao.autorite_contractante = "MAERAH / DMP"
    ao.description           = "Fourniture ordinateurs et imprimantes"
    ao.date_cloture          = date.today() + timedelta(days=15)
    ao.est_urgent            = False
    ao.jours_restants        = 15
    for k, v in kwargs.items():
        setattr(ao, k, v)
    return ao

def make_abonne(plan="pro"):
    ab = MagicMock()
    ab.id       = uuid4()
    ab.prenom   = "Adama"
    ab.nom      = "Kabore"
    ab.email    = "adama@test.bf"
    ab.whatsapp = "+226 70 12 34 56"
    ab.plan     = plan
    ab.entreprise = "BTP Kabore SARL"
    return ab

# ── Tests checklist ───────────────────────────────────────────────────────────

class TestChecklist:

    def test_checklist_ouvert_8_pieces(self):
        from backend_candidatures import get_checklist
        cl = get_checklist("ouvert")
        assert len(cl) == 8

    def test_checklist_ouvert_asf_obligatoire(self):
        from backend_candidatures import get_checklist
        cl = get_checklist("ouvert")
        asf = next((p for p in cl if p["type"] == "asf"), None)
        assert asf is not None
        assert asf["obligatoire"] is True
        assert asf["validite_jours"] == 90

    def test_checklist_dpx_simplifie(self):
        from backend_candidatures import get_checklist
        cl_ouvert = get_checklist("ouvert")
        cl_dpx    = get_checklist("dpx")
        assert len(cl_dpx) < len(cl_ouvert)

    def test_checklist_ami_cv_obligatoire(self):
        from backend_candidatures import get_checklist
        cl = get_checklist("ami")
        cv = next((p for p in cl if p["type"] == "cv"), None)
        assert cv is not None
        assert cv["obligatoire"] is True

    def test_checklist_type_inconnu_retourne_ouvert(self):
        from backend_candidatures import get_checklist
        cl = get_checklist("type_inexistant")
        assert len(cl) > 0  # Retourne la checklist ouvert par défaut

    def test_toutes_pieces_ont_label(self):
        from backend_candidatures import get_checklist, PIECES_PAR_TYPE
        for type_proc in PIECES_PAR_TYPE:
            for piece in get_checklist(type_proc):
                assert "label" in piece and len(piece["label"]) > 0

# ── Tests avancement ─────────────────────────────────────────────────────────

class TestAvancement:

    def test_avancement_zero_sans_pieces(self):
        from backend_candidatures import calculer_avancement
        db = MagicMock()
        # Candidature sans pièces ni offre
        db.execute.return_value.fetchone.return_value = MagicMock(
            abonne_id=uuid4(), type_procedure="ouvert"
        )
        db.execute.return_value.fetchall.return_value = []
        db.execute.return_value.scalar.return_value = 0

        result = calculer_avancement(str(uuid4()), db)
        assert result["score_global"] >= 0
        assert result["pret_depot"] is False

    def test_avancement_avec_blocages(self):
        from backend_candidatures import calculer_avancement
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = MagicMock(
            abonne_id=uuid4(), type_procedure="ouvert"
        )
        db.execute.return_value.fetchall.return_value = []
        db.execute.return_value.scalar.return_value = 2  # 2 pièces expirées

        result = calculer_avancement(str(uuid4()), db)
        assert len(result["blocages"]) > 0

    def test_score_maximum_100(self):
        """Le score ne doit jamais dépasser 100."""
        from backend_candidatures import calculer_avancement
        db = MagicMock()
        # Simuler un dossier parfait
        abonne_id = uuid4()
        cand_id   = str(uuid4())

        call_count = 0
        def mock_execute(query, params=None):
            nonlocal call_count
            result = MagicMock()
            call_count += 1
            # Pièces — toutes valides
            if "pieces_administratives" in str(query) and "est_valide" in str(query):
                result.fetchall.return_value = [
                    MagicMock(type_piece=t) for t in
                    ["asf","cnss","aje","rccm","ifu","statuts","reference_marche","attestation_bancaire"]
                ]
            elif "offres_generees" in str(query):
                result.fetchone.return_value = MagicMock(valide_par_user=True)
            elif "taches_candidature" in str(query):
                result.fetchall.return_value = [MagicMock(statut="fait")] * 5
            elif "scalar" in str(dir(result)):
                result.scalar.return_value = 0
            else:
                result.fetchone.return_value = MagicMock(
                    abonne_id=abonne_id, type_procedure="ouvert"
                )
            return result

        db.execute = mock_execute
        result = calculer_avancement(cand_id, db)
        assert result.get("score_global", 0) <= 100


# ── Tests endpoint create ─────────────────────────────────────────────────────

class TestCreateCandidature:

    def test_creation_standard(self):
        db    = MagicMock()
        abonne = make_abonne()
        ao     = make_ao()

        # AO trouvé
        db.execute.return_value.fetchone.side_effect = [
            MagicMock(id=ao.id, type_procedure="ouvert"),  # AO existe
            None,  # Pas de doublon
        ]
        db.execute.return_value.fetchall.return_value = []

        from backend_candidatures import CandidatureCreate, create_candidature
        body   = CandidatureCreate(ao_id=ao.id)
        result = create_candidature(body, abonne, db)

        assert "id" in result
        assert result["statut"] == "en_veille"
        db.commit.assert_called_once()

    def test_creation_doublon_rejete(self):
        from fastapi import HTTPException
        from backend_candidatures import CandidatureCreate, create_candidature

        db     = MagicMock()
        abonne = make_abonne()
        ao     = make_ao()

        db.execute.return_value.fetchone.side_effect = [
            MagicMock(id=ao.id, type_procedure="ouvert"),  # AO existe
            MagicMock(id=uuid4()),  # Doublon trouvé
        ]

        body = CandidatureCreate(ao_id=ao.id)
        with pytest.raises(HTTPException) as exc:
            create_candidature(body, abonne, db)
        assert exc.value.status_code == 409

    def test_ao_inexistant_404(self):
        from fastapi import HTTPException
        from backend_candidatures import CandidatureCreate, create_candidature

        db     = MagicMock()
        abonne = make_abonne()

        db.execute.return_value.fetchone.return_value = None  # AO non trouvé

        body = CandidatureCreate(ao_id=uuid4())
        with pytest.raises(HTTPException) as exc:
            create_candidature(body, abonne, db)
        assert exc.value.status_code == 404


# ── Tests génération offre IA ─────────────────────────────────────────────────

class TestGenererOffre:

    @patch("backend_candidatures.anthropic")
    def test_generation_succes(self, mock_anthropic):
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="# Offre technique\n\nContenu généré...")]
        mock_message.usage.output_tokens = 512
        mock_client.messages.create.return_value = mock_message

        db = MagicMock()
        db.execute.return_value.fetchone.return_value = MagicMock(
            titre="Acquisition matériel IT",
            autorite_contractante="MAERAH",
            type_procedure="ouvert",
            secteur="informatique",
            description="Fourniture ordinateurs"
        )

        abonne = make_abonne()
        abonne.entreprise = "BTP Kabore SARL"

        from backend_candidatures import generer_offre, OffreGenererRequest
        import asyncio
        body   = OffreGenererRequest(type_offre="technique")
        result = asyncio.run(generer_offre(str(uuid4()), body, abonne, db))

        assert "offre_id" in result
        assert "contenu" in result
        assert len(result["contenu"]) > 50
        db.commit.assert_called_once()

    @patch("backend_candidatures.anthropic")
    def test_generation_erreur_claude(self, mock_anthropic):
        from fastapi import HTTPException
        from backend_candidatures import generer_offre, OffreGenererRequest
        import asyncio

        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")

        db = MagicMock()
        db.execute.return_value.fetchone.return_value = MagicMock(
            titre="Test", autorite_contractante="Test",
            type_procedure="ouvert", secteur="autre", description=""
        )

        abonne = make_abonne()
        body   = OffreGenererRequest()

        with pytest.raises(HTTPException) as exc:
            asyncio.run(generer_offre(str(uuid4()), body, abonne, db))
        assert exc.value.status_code == 503


# ── Tests upload pièce ────────────────────────────────────────────────────────

class TestUploadPiece:

    @pytest.mark.asyncio
    async def test_fichier_trop_grand_rejete(self):
        from fastapi import HTTPException, UploadFile
        from backend_candidatures import upload_piece

        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "application/pdf"
        mock_file.filename = "test.pdf"
        # Fichier de 11 MB
        mock_file.read = MagicMock(return_value=b"x" * (11 * 1024 * 1024))

        db     = MagicMock()
        abonne = make_abonne()

        with pytest.raises(HTTPException) as exc:
            await upload_piece("asf", None, None, None, mock_file, abonne, db)
        assert exc.value.status_code == 422

    @pytest.mark.asyncio
    async def test_format_non_supporte_rejete(self):
        from fastapi import HTTPException, UploadFile
        from backend_candidatures import upload_piece

        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "text/csv"
        mock_file.filename = "test.csv"
        mock_file.read = MagicMock(return_value=b"data")

        db     = MagicMock()
        abonne = make_abonne()

        with pytest.raises(HTTPException) as exc:
            await upload_piece("asf", None, None, None, mock_file, abonne, db)
        assert exc.value.status_code == 422
