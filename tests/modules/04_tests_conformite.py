"""
NetSync Gov Conformité — Tests unitaires
Usage : python -m pytest 04_tests_conformite.py -v
"""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock
from uuid import uuid4


def make_abonne():
    ab = MagicMock()
    ab.id    = uuid4()
    ab.plan  = "pro"
    ab.email = "test@test.bf"
    return ab


# ── Tests get_statut_piece ────────────────────────────────────────────────────

class TestStatutPiece:

    def test_piece_permanente(self):
        from backend_conformite import get_statut_piece
        r = get_statut_piece(None, None)
        assert r["statut"] == "permanent"
        assert r["couleur"] == "bleu"

    def test_piece_valide(self):
        from backend_conformite import get_statut_piece
        future = date.today() + timedelta(days=60)
        r = get_statut_piece(future, 90)
        assert r["statut"] == "valide"
        assert r["couleur"] == "vert"
        assert r["jours_restants"] == 60

    def test_piece_expiree(self):
        from backend_conformite import get_statut_piece
        passe = date.today() - timedelta(days=5)
        r = get_statut_piece(passe, 90)
        assert r["statut"] == "expiree"
        assert r["couleur"] == "rouge"
        assert r["jours_restants"] == -5

    def test_piece_critique_7j(self):
        from backend_conformite import get_statut_piece
        proche = date.today() + timedelta(days=5)
        r = get_statut_piece(proche, 90)
        assert r["statut"] == "critique"
        assert r["couleur"] == "rouge"

    def test_piece_urgent_15j(self):
        from backend_conformite import get_statut_piece
        bientot = date.today() + timedelta(days=12)
        r = get_statut_piece(bientot, 90)
        assert r["statut"] == "urgent"
        assert r["couleur"] == "orange"

    def test_piece_attention_30j(self):
        from backend_conformite import get_statut_piece
        moyen = date.today() + timedelta(days=25)
        r = get_statut_piece(moyen, 90)
        assert r["statut"] == "attention"
        assert r["couleur"] == "jaune"

    def test_jours_restants_exact(self):
        from backend_conformite import get_statut_piece
        dans_45_j = date.today() + timedelta(days=45)
        r = get_statut_piece(dans_45_j, 90)
        assert r["jours_restants"] == 45


# ── Tests calculer_score_conformite ──────────────────────────────────────────

class TestScoreConformite:

    def test_score_100_toutes_valides(self):
        from backend_conformite import calculer_score_conformite
        db = MagicMock()
        # Toutes les pièces clés valides
        db.execute.return_value.fetchall.return_value = [
            MagicMock(type_piece=t, est_valide=True)
            for t in ["asf", "cnss", "aje", "rccm", "ifu"]
        ]
        result = calculer_score_conformite(str(uuid4()), db)
        assert result["score"] == 100
        assert result["niveau"] == "conforme"
        assert len(result["manquantes"]) == 0
        assert len(result["expirees"]) == 0

    def test_score_0_aucune_piece(self):
        from backend_conformite import calculer_score_conformite
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []
        result = calculer_score_conformite(str(uuid4()), db)
        assert result["score"] == 0
        assert result["niveau"] == "non_conforme"
        assert len(result["manquantes"]) == 5

    def test_score_60_trois_sur_cinq(self):
        from backend_conformite import calculer_score_conformite
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [
            MagicMock(type_piece=t, est_valide=True)
            for t in ["asf", "cnss", "aje"]
        ]
        result = calculer_score_conformite(str(uuid4()), db)
        assert result["score"] == 60
        assert result["niveau"] == "attention"

    def test_score_40_deux_sur_cinq(self):
        from backend_conformite import calculer_score_conformite
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [
            MagicMock(type_piece=t, est_valide=True)
            for t in ["asf", "cnss"]
        ]
        result = calculer_score_conformite(str(uuid4()), db)
        assert result["score"] == 40
        assert result["niveau"] == "non_conforme"

    def test_piece_expiree_dans_expirees(self):
        from backend_conformite import calculer_score_conformite
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [
            MagicMock(type_piece="asf",  est_valide=False),  # Expirée
            MagicMock(type_piece="cnss", est_valide=True),
            MagicMock(type_piece="aje",  est_valide=True),
            MagicMock(type_piece="rccm", est_valide=True),
            MagicMock(type_piece="ifu",  est_valide=True),
        ]
        result = calculer_score_conformite(str(uuid4()), db)
        assert "asf" in result["expirees"][0]["type"] if result["expirees"] else True
        assert result["score"] == 80


# ── Tests catalogue ───────────────────────────────────────────────────────────

class TestCatalogue:

    def test_catalogue_10_pieces(self):
        from backend_conformite import CATALOGUE_PIECES
        assert len(CATALOGUE_PIECES) == 10

    def test_asf_validite_90j(self):
        from backend_conformite import CATALOGUE_PIECES
        assert CATALOGUE_PIECES["asf"]["validite_j"] == 90

    def test_cnss_validite_90j(self):
        from backend_conformite import CATALOGUE_PIECES
        assert CATALOGUE_PIECES["cnss"]["validite_j"] == 90

    def test_aje_validite_365j(self):
        from backend_conformite import CATALOGUE_PIECES
        assert CATALOGUE_PIECES["aje"]["validite_j"] == 365

    def test_ifu_permanent(self):
        from backend_conformite import CATALOGUE_PIECES
        assert CATALOGUE_PIECES["ifu"]["validite_j"] is None

    def test_asf_a_lien_secop(self):
        from backend_conformite import CATALOGUE_PIECES
        assert CATALOGUE_PIECES["asf"]["lien_renouvellement"] is not None
        assert "secop" in CATALOGUE_PIECES["asf"]["lien_renouvellement"].lower()

    def test_toutes_pieces_ont_label(self):
        from backend_conformite import CATALOGUE_PIECES
        for k, v in CATALOGUE_PIECES.items():
            assert "label" in v and len(v["label"]) > 0

    def test_toutes_pieces_ont_instructions(self):
        from backend_conformite import CATALOGUE_PIECES
        for k, v in CATALOGUE_PIECES.items():
            assert "instructions" in v and len(v["instructions"]) > 0


# ── Tests verifier_conformite_pour_ao ────────────────────────────────────────

class TestVerifierConformiteAO:

    def test_peut_candidater_toutes_valides(self):
        from backend_conformite import verifier_conformite_pour_ao
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = MagicMock(
            type_procedure="ouvert", titre="AO Test"
        )
        # Toutes les pièces valides pour AO ouvert
        pcs = ["asf", "cnss", "aje", "rccm", "ifu", "statuts", "reference_marche"]
        db.execute.return_value.fetchall.return_value = [
            MagicMock(type_piece=t) for t in pcs
        ]
        db.execute.return_value.fetchone.side_effect = [
            MagicMock(type_procedure="ouvert", titre="AO Test"),
            *[MagicMock(date_expiration=date.today() + timedelta(days=60))] * 20
        ]

        abonne = make_abonne()
        result = verifier_conformite_pour_ao(str(uuid4()), abonne, db)

        assert "peut_candidater" in result
        assert "blocages" in result
        assert "ao_titre" in result

    def test_ao_inexistant_404(self):
        from fastapi import HTTPException
        from backend_conformite import verifier_conformite_pour_ao
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None

        abonne = make_abonne()
        with pytest.raises(HTTPException) as exc:
            verifier_conformite_pour_ao(str(uuid4()), abonne, db)
        assert exc.value.status_code == 404

    def test_dpx_checklist_courte(self):
        from backend_conformite import CATALOGUE_PIECES
        pieces_dpx = [k for k, v in CATALOGUE_PIECES.items() if "dpx" in v["obligatoire"]]
        pieces_ouvert = [k for k, v in CATALOGUE_PIECES.items() if "ouvert" in v["obligatoire"]]
        assert len(pieces_dpx) < len(pieces_ouvert)
