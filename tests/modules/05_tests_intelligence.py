"""
NetSync Gov Intelligence — Tests
Usage : python -m pytest 05_tests_intelligence.py -v
"""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4


def make_db_with_data():
    """Mock DB avec données réalistes."""
    db = MagicMock()

    # Stats globales
    stats_row = MagicMock()
    stats_row.total              = 450
    stats_row.ao_ce_mois         = 38
    stats_row.ao_hier            = 12
    stats_row.montant_total      = 45_000_000_000
    stats_row.top_secteur        = "informatique"
    stats_row.tendance_pct       = 12.5

    # Résumé
    db.execute.return_value.scalar.side_effect = [450, 38, 12, 45_000_000_000, 35]
    db.execute.return_value.fetchone.return_value = MagicMock(
        secteur="informatique", nb=15
    )

    return db


def make_abonne():
    ab = MagicMock()
    ab.id    = uuid4()
    ab.plan  = "pro"
    ab.email = "test@test.bf"
    return ab


# ── Tests helpers ─────────────────────────────────────────────────────────────

class TestPeriodeToDates:

    def test_7j(self):
        from backend_intelligence import periode_to_dates
        debut, fin = periode_to_dates("7j")
        assert (fin - debut).days == 7

    def test_30j(self):
        from backend_intelligence import periode_to_dates
        debut, fin = periode_to_dates("30j")
        assert (fin - debut).days == 30

    def test_12m(self):
        from backend_intelligence import periode_to_dates
        debut, fin = periode_to_dates("12m")
        assert (fin - debut).days == 365

    def test_24m(self):
        from backend_intelligence import periode_to_dates
        debut, fin = periode_to_dates("24m")
        assert (fin - debut).days == 730

    def test_inconnu_retourne_12m(self):
        from backend_intelligence import periode_to_dates
        debut, fin = periode_to_dates("inconnu")
        assert (fin - debut).days == 365

    def test_fin_est_aujourd_hui(self):
        from backend_intelligence import periode_to_dates
        _, fin = periode_to_dates("30j")
        assert fin == date.today()


# ── Tests endpoint tendances secteurs ────────────────────────────────────────

class TestTendancesSecteurs:

    def test_retourne_liste_secteurs(self):
        from backend_intelligence import tendances_par_secteur

        db = MagicMock()
        rows = []
        for secteur, nb in [("informatique", 45), ("btp", 38), ("sante", 22)]:
            r = MagicMock()
            r.secteur               = secteur
            r.nb_ao                 = nb
            r.nb_ouverts            = nb // 2
            r.montant_moyen         = 25_000_000
            r.montant_total         = nb * 25_000_000
            r.derniere_publication  = date.today()
            rows.append(r)
        db.execute.return_value.fetchall.return_value = rows

        abonne = make_abonne()
        result = tendances_par_secteur("12m", abonne, db)

        assert "secteurs" in result
        assert len(result["secteurs"]) == 3
        assert result["secteurs"][0]["secteur"] == "informatique"
        assert result["secteurs"][0]["nb_ao"] == 45

    def test_periode_incluse_dans_reponse(self):
        from backend_intelligence import tendances_par_secteur

        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []
        abonne = make_abonne()

        result = tendances_par_secteur("6m", abonne, db)
        assert result["periode"] == "6m"
        assert "date_debut" in result
        assert "date_fin" in result


# ── Tests endpoint évolution ──────────────────────────────────────────────────

class TestEvolutionMensuelle:

    def test_evolution_avec_filtre_secteur(self):
        from backend_intelligence import evolution_mensuelle

        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [
            MagicMock(mois=date(2026, 1, 1), mois_label_mock="janv. 2026",
                      nb_ao=12, montant_moyen=20_000_000, montant_total=240_000_000),
        ]
        # Patcher strftime
        import unittest.mock as mock
        with mock.patch.object(date, 'strftime', return_value="janv. 2026"):
            abonne = make_abonne()
            result = evolution_mensuelle("12m", "informatique", abonne, db)

        assert "evolution" in result
        assert result["secteur"] == "informatique"

    def test_evolution_sans_secteur(self):
        from backend_intelligence import evolution_mensuelle

        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []
        abonne = make_abonne()

        result = evolution_mensuelle("12m", None, abonne, db)
        assert result["secteur"] is None


# ── Tests endpoint top autorités ──────────────────────────────────────────────

class TestTopAutorites:

    def test_limite_respecte(self):
        from backend_intelligence import top_autorites

        db = MagicMock()
        rows = []
        for i in range(5):
            r = MagicMock()
            r.autorite_contractante = f"Ministère {i}"
            r.nb_ao                 = 10 - i
            r.montant_moyen         = 20_000_000
            r.montant_total         = (10 - i) * 20_000_000
            r.derniere_publication  = date.today()
            r.nb_secteurs           = 2
            rows.append(r)
        db.execute.return_value.fetchall.return_value = rows

        abonne = make_abonne()
        result = top_autorites(5, "12m", None, abonne, db)

        assert len(result["autorites"]) == 5
        assert result["autorites"][0]["nom"] == "Ministère 0"


# ── Tests endpoint résumé ─────────────────────────────────────────────────────

class TestResume:

    def test_resume_retourne_tous_champs(self):
        from backend_intelligence import resume_commande_publique

        db = MagicMock()
        # scalar() appelé 4 fois : total, ce_mois, hier, montant_total, mois_dernier
        db.execute.return_value.scalar.side_effect = [450, 38, 12, 45_000_000_000, 34]
        db.execute.return_value.fetchone.return_value = MagicMock(secteur="informatique")

        abonne = make_abonne()
        result = resume_commande_publique(abonne, db)

        assert "total_ao_indexes" in result
        assert "ao_ce_mois" in result
        assert "ao_hier" in result
        assert "top_secteur_ce_mois" in result
        assert "tendance_vs_mois_pct" in result
        assert "derniere_mise_a_jour" in result

    def test_tendance_positive(self):
        from backend_intelligence import resume_commande_publique

        db = MagicMock()
        # ce_mois=40, mois_dernier=32 → tendance = +25%
        db.execute.return_value.scalar.side_effect = [450, 40, 12, 0, 32]
        db.execute.return_value.fetchone.return_value = MagicMock(secteur="btp")

        abonne = make_abonne()
        result = resume_commande_publique(abonne, db)

        assert result["tendance_vs_mois_pct"] > 0


# ── Tests stats publiques ─────────────────────────────────────────────────────

class TestStatsPubliques:

    def test_pas_auth_requise(self):
        """L'endpoint public ne requiert pas d'authentification."""
        from backend_intelligence import stats_publiques

        db = MagicMock()
        db.execute.return_value.scalar.side_effect = [450, 87, 38]

        result = stats_publiques(db)
        assert "total_indexes" in result
        assert "source" in result
        assert "NetSync Gov" in result["source"]
        assert "note" in result


# ── Tests génération rapport PDF ──────────────────────────────────────────────

class TestGenererRapport:

    def test_mois_invalide_rejete(self):
        from fastapi import HTTPException
        from backend_intelligence import generer_rapport_mensuel
        import asyncio

        db = MagicMock()
        abonne = make_abonne()

        with pytest.raises(HTTPException) as exc:
            asyncio.run(generer_rapport_mensuel("format-invalide", abonne, db))
        assert exc.value.status_code == 422

    @patch("backend_intelligence.anthropic")
    def test_rapport_genere_sans_erreur(self, mock_anthropic):
        """Test que le rapport se génère même sans vraies données."""
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text="Analyse test du marché burkinabè.")]
        mock_client.messages.create.return_value = mock_msg

        import asyncio
        from backend_intelligence import generer_rapport_mensuel
        from fastapi.responses import StreamingResponse

        db = MagicMock()
        # Simuler les stats mois
        stats_mock = MagicMock()
        stats_mock.total         = 38
        stats_mock.btp           = 12
        stats_mock.it            = 8
        stats_mock.sante         = 5
        stats_mock.agriculture   = 4
        stats_mock.conseil       = 3
        stats_mock.montant_moyen = 25_000_000
        stats_mock.montant_total = 800_000_000
        stats_mock.ao_ouverts    = 25
        stats_mock.dpx           = 10

        db.execute.return_value.fetchone.return_value  = stats_mock
        db.execute.return_value.fetchall.return_value  = []

        abonne = make_abonne()
        result = asyncio.run(generer_rapport_mensuel("2026-03", abonne, db))

        assert isinstance(result, StreamingResponse)
        assert result.media_type == "application/pdf"
