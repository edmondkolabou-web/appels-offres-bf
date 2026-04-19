"""
NetSync Gov Institutions — Tests unitaires et d'intégration
Usage : python -m pytest 04_tests_institutions.py -v
"""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4


def make_abonne(plan="pro"):
    ab = MagicMock()
    ab.id    = uuid4()
    ab.plan  = plan
    ab.email = "test@ministere.bf"
    return ab


def make_institution(plan="gratuit"):
    inst = MagicMock()
    inst.id              = uuid4()
    inst.nom             = "Ministère de l'Agriculture"
    inst.sigle           = "MAERAH"
    inst.slug            = "maerah"
    inst.type_institution = "ministere"
    inst.secteurs        = ["agriculture", "eau"]
    inst.region          = "Ouagadougou"
    inst.plan            = plan
    inst.verifie         = True
    inst.email_contact   = "dmp@maerah.bf"
    inst.abonne_id       = uuid4()
    return inst


# ── Tests generate_slug ───────────────────────────────────────────────────────

class TestGenerateSlug:

    def test_slug_simple(self):
        from backend_institutions import generate_slug
        assert generate_slug("Ministère de l'Agriculture") == "ministere-de-l-agriculture"

    def test_slug_accents(self):
        from backend_institutions import generate_slug
        assert "e" in generate_slug("Éducation Nationale")

    def test_slug_caracteres_speciaux(self):
        from backend_institutions import generate_slug
        slug = generate_slug("MAERAH / SG / DMP")
        assert "/" not in slug
        assert " " not in slug

    def test_slug_max_80_chars(self):
        from backend_institutions import generate_slug
        long_name = "A" * 200
        assert len(generate_slug(long_name)) <= 80

    def test_slug_minuscules(self):
        from backend_institutions import generate_slug
        assert generate_slug("MENA").islower() or generate_slug("MENA") == "mena"


# ── Tests creer_institution ───────────────────────────────────────────────────

class TestCreerInstitution:

    def test_creation_standard(self):
        from backend_institutions import creer_institution, InstitutionCreate
        db = MagicMock()
        db.execute.return_value.fetchone.side_effect = [None, None]  # Pas de doublon slug, pas d'existing
        db.execute.return_value.fetchone.return_value = None

        abonne = make_abonne()
        body   = InstitutionCreate(
            nom="Ministère de l'Agriculture",
            type_institution="ministere",
            secteurs=["agriculture"]
        )
        result = creer_institution(body, abonne, db)

        assert "id" in result
        assert "slug" in result
        assert "url_profil" in result
        assert "minist" in result["slug"]
        db.commit.assert_called_once()

    def test_doublon_institution_rejete(self):
        from fastapi import HTTPException
        from backend_institutions import creer_institution, InstitutionCreate
        db = MagicMock()

        # Abonné a déjà une institution
        db.execute.return_value.fetchone.side_effect = [
            None,  # Slug disponible
            MagicMock(id=uuid4()),  # Institution existante → doublon
        ]

        abonne = make_abonne()
        body   = InstitutionCreate(nom="Autre institution", type_institution="ministere")

        with pytest.raises(HTTPException) as exc:
            creer_institution(body, abonne, db)
        assert exc.value.status_code == 409

    def test_slug_unique_incremente(self):
        """Si le slug existe déjà, il doit être incrémenté."""
        from backend_institutions import creer_institution, InstitutionCreate
        db = MagicMock()

        call_count = 0
        def mock_fetchone(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return MagicMock()   # Slug existe → incrémenter
            return None              # Slug incrémenté dispo + pas d'existing

        db.execute.return_value.fetchone.side_effect = mock_fetchone

        abonne = make_abonne()
        body   = InstitutionCreate(nom="Test", type_institution="autre")
        result = creer_institution(body, abonne, db)

        assert result["slug"].endswith("-1") or "-" in result["slug"]


# ── Tests dashboard ───────────────────────────────────────────────────────────

class TestDashboard:

    def test_dashboard_institution_introuvable(self):
        from fastapi import HTTPException
        from backend_institutions import dashboard_institution
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None

        abonne = make_abonne()
        with pytest.raises(HTTPException) as exc:
            dashboard_institution(abonne, db)
        assert exc.value.status_code == 404

    def test_dashboard_retourne_structure_complete(self):
        from backend_institutions import dashboard_institution
        db = MagicMock()

        stats_mock = MagicMock()
        stats_mock.total_ao      = 25
        stats_mock.ao_ouverts    = 8
        stats_mock.ao_clotures   = 12
        stats_mock.ao_attribues  = 5
        stats_mock.ao_ce_mois    = 3
        stats_mock.montant_moyen = 45_000_000
        stats_mock.montant_total = 1_125_000_000
        stats_mock.delai_moyen_j = 21

        inst = make_institution()
        db.execute.return_value.fetchone.side_effect = [
            inst,        # Institution
            stats_mock,  # Stats
        ]
        db.execute.return_value.fetchall.return_value = []

        abonne = make_abonne()
        result = dashboard_institution(abonne, db)

        assert "institution" in result
        assert "stats" in result
        assert "evolution_6m" in result
        assert "par_secteur" in result
        assert "ao_urgents" in result
        assert result["stats"]["total_ao"] == 25


# ── Tests enrichir_ao ─────────────────────────────────────────────────────────

class TestEnrichirAO:

    def test_enrichissement_standard(self):
        from backend_institutions import enrichir_ao, AOEnrichissement
        db = MagicMock()
        inst = make_institution()

        db.execute.return_value.fetchone.side_effect = [
            inst,  # Institution trouvée
            MagicMock(id=uuid4(), institution_id=None),  # AO sans institution
        ]

        abonne = make_abonne()
        body   = AOEnrichissement(
            ao_id=uuid4(),
            contact_nom="Directeur des Marchés",
            region_exacte="Ouagadougou Centre"
        )
        result = enrichir_ao(body, abonne, db)

        assert result["message"] == "AO enrichi avec succès"
        db.commit.assert_called_once()

    def test_ao_appartenant_a_autre_institution_rejete(self):
        from fastapi import HTTPException
        from backend_institutions import enrichir_ao, AOEnrichissement
        db = MagicMock()

        inst = make_institution()
        autre_id = uuid4()

        db.execute.return_value.fetchone.side_effect = [
            inst,
            MagicMock(id=uuid4(), institution_id=autre_id),  # AO d'une autre institution
        ]

        abonne = make_abonne()
        body   = AOEnrichissement(ao_id=uuid4(), contact_nom="DMP")

        with pytest.raises(HTTPException) as exc:
            enrichir_ao(body, abonne, db)
        assert exc.value.status_code == 403

    def test_ao_inexistant_404(self):
        from fastapi import HTTPException
        from backend_institutions import enrichir_ao, AOEnrichissement
        db = MagicMock()
        inst = make_institution()

        db.execute.return_value.fetchone.side_effect = [
            inst,   # Institution trouvée
            None,   # AO non trouvé
        ]

        abonne = make_abonne()
        body   = AOEnrichissement(ao_id=uuid4())

        with pytest.raises(HTTPException) as exc:
            enrichir_ao(body, abonne, db)
        assert exc.value.status_code == 404


# ── Tests notifier soumissionnaires ───────────────────────────────────────────

class TestNotifierSoumissionnaires:

    def test_plan_gratuit_bloque(self):
        from fastapi import HTTPException
        from backend_institutions import notifier_soumissionnaires, NotificationCiblee
        db = MagicMock()

        inst = make_institution(plan="gratuit")
        db.execute.return_value.fetchone.return_value = inst

        abonne = make_abonne()
        body   = NotificationCiblee(
            ao_id=uuid4(),
            secteurs_cibles=["informatique"]
        )

        with pytest.raises(HTTPException) as exc:
            notifier_soumissionnaires(body, abonne, db)
        assert exc.value.status_code == 402

    def test_plan_institutionnel_autorise(self):
        from backend_institutions import notifier_soumissionnaires, NotificationCiblee
        db = MagicMock()

        inst = make_institution(plan="institutionnel")
        ao_mock = MagicMock()
        ao_mock.titre         = "Acquisition matériel"
        ao_mock.date_cloture  = date.today() + timedelta(days=10)

        db.execute.return_value.fetchone.side_effect = [inst, ao_mock]
        db.execute.return_value.scalar.return_value  = 42  # 42 abonnés ciblés

        abonne = make_abonne()
        body   = NotificationCiblee(
            ao_id=uuid4(),
            secteurs_cibles=["informatique", "btp"]
        )
        result = notifier_soumissionnaires(body, abonne, db)

        assert "message" in result
        assert result["cout_fcfa"] == 5_000
        assert result["cibles_count"] == 42

    def test_aucun_abonne_cible(self):
        from backend_institutions import notifier_soumissionnaires, NotificationCiblee
        db = MagicMock()

        inst = make_institution(plan="institutionnel")
        ao_mock = MagicMock(titre="Test", date_cloture=date.today() + timedelta(days=5))

        db.execute.return_value.fetchone.side_effect = [inst, ao_mock]
        db.execute.return_value.scalar.return_value  = 0  # Aucun abonné

        abonne = make_abonne()
        body   = NotificationCiblee(ao_id=uuid4(), secteurs_cibles=["rare"])
        result = notifier_soumissionnaires(body, abonne, db)

        assert result["envoyes"] == 0


# ── Tests profil public ───────────────────────────────────────────────────────

class TestProfilPublic:

    def test_profil_inexistant_404(self):
        from fastapi import HTTPException
        from backend_institutions import profil_institution_public
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None

        with pytest.raises(HTTPException) as exc:
            profil_institution_public("slug-inexistant", db)
        assert exc.value.status_code == 404

    def test_profil_retourne_structure(self):
        from backend_institutions import profil_institution_public
        db = MagicMock()

        inst = make_institution()
        stats_mock = MagicMock()
        stats_mock.total           = 30
        stats_mock.ouverts         = 8
        stats_mock.montant_moyen   = 40_000_000
        stats_mock.montant_total   = 1_200_000_000
        stats_mock.derniere_publication = date.today()

        db.execute.return_value.fetchone.side_effect = [inst, stats_mock]
        db.execute.return_value.fetchall.return_value = []

        result = profil_institution_public("maerah", db)

        assert "institution" in result
        assert "stats" in result
        assert "par_secteur" in result
        assert "derniers_ao" in result
        assert result["stats"]["total_ao"] == 30
