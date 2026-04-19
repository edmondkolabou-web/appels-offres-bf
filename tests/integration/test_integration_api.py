"""
NetSync Gov — Tests d'intégration API FastAPI (TestClient)
Couvre les endpoints principaux avec une BDD en mémoire SQLite.
Usage : python -m pytest test_integration_api.py -v
"""
import pytest
from datetime import date, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ── Setup BDD de test ─────────────────────────────────────────────────────────

DATABASE_URL_TEST = "sqlite:///./test_netsync.db"


@pytest.fixture(scope="session")
def test_db():
    """BDD SQLite en mémoire pour les tests."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / 'api_netsync_gov'))
    sys.path.insert(0, str(Path(__file__).parent.parent / 'pipeline_netsync_gov'))

    from models import Base
    engine = create_engine(
        DATABASE_URL_TEST,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    yield TestingSessionLocal

    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test_netsync.db"):
        os.remove("./test_netsync.db")


@pytest.fixture(scope="session")
def client(test_db):
    """Client de test FastAPI avec override de la BDD."""
    from api.main import app
    from api.database import get_db

    def override_get_db():
        db = test_db()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c


# ── Tests Auth ────────────────────────────────────────────────────────────────

class TestAuth:

    def test_register_success(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email":    "test@netsync.bf",
            "password": "motdepasse123",
            "prenom":   "Adama",
            "nom":      "Kabore",
            "plan":     "gratuit",
            "secteurs": ["informatique"],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["plan"] == "gratuit"

    def test_register_email_duplique(self, client):
        # Premier enregistrement
        client.post("/api/v1/auth/register", json={
            "email": "doublon@netsync.bf", "password": "pass12345",
            "prenom": "A", "nom": "B", "plan": "gratuit", "secteurs": [],
        })
        # Deuxième avec le même email
        resp = client.post("/api/v1/auth/register", json={
            "email": "doublon@netsync.bf", "password": "pass12345",
            "prenom": "A", "nom": "B", "plan": "gratuit", "secteurs": [],
        })
        assert resp.status_code == 409

    def test_login_success(self, client):
        # Créer un compte d'abord
        client.post("/api/v1/auth/register", json={
            "email": "login_test@netsync.bf", "password": "motdepasse123",
            "prenom": "Edmond", "nom": "K", "plan": "gratuit", "secteurs": [],
        })
        resp = client.post("/api/v1/auth/login", json={
            "email": "login_test@netsync.bf",
            "password": "motdepasse123",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_mauvais_mot_de_passe(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "email": "test@netsync.bf",
            "password": "mauvais_mdp",
        })
        assert resp.status_code == 401

    def test_me_sans_token(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_me_avec_token(self, client):
        # Créer un compte et récupérer le token
        reg = client.post("/api/v1/auth/register", json={
            "email": "me_test@netsync.bf", "password": "motdepasse123",
            "prenom": "Test", "nom": "User", "plan": "gratuit", "secteurs": [],
        })
        token = reg.json()["access_token"]
        resp = client.get("/api/v1/auth/me",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["email"] == "me_test@netsync.bf"

    def test_password_trop_court(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "short@test.bf", "password": "abc",
            "prenom": "A", "nom": "B", "plan": "gratuit", "secteurs": [],
        })
        assert resp.status_code == 422


# ── Tests AOs ────────────────────────────────────────────────────────────────

class TestAOs:

    @pytest.fixture
    def auth_headers(self, client):
        """Token d'authentification pour les tests AO."""
        reg = client.post("/api/v1/auth/register", json={
            "email": f"ao_user_{uuid4().hex[:6]}@test.bf",
            "password": "motdepasse123",
            "prenom": "Test", "nom": "AO",
            "plan": "gratuit", "secteurs": [],
        })
        token = reg.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_list_aos_sans_token(self, client):
        resp = client.get("/api/v1/aos")
        assert resp.status_code == 401

    def test_list_aos_avec_token(self, client, auth_headers):
        resp = client.get("/api/v1/aos", headers=auth_headers)
        assert resp.status_code in (200, 402)  # 402 si limite gratuite atteinte
        if resp.status_code == 200:
            data = resp.json()
            assert "items" in data
            assert "total" in data
            assert "pages" in data

    def test_list_aos_pagination(self, client, auth_headers):
        resp = client.get("/api/v1/aos?page=1&per_page=5", headers=auth_headers)
        if resp.status_code == 200:
            data = resp.json()
            assert data["per_page"] == 5
            assert data["page"] == 1

    def test_ao_inexistant(self, client, auth_headers):
        fake_id = str(uuid4())
        resp = client.get(f"/api/v1/aos/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404

    def test_secteurs(self, client):
        resp = client.get("/api/v1/aos/secteurs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ── Tests Alertes ─────────────────────────────────────────────────────────────

class TestAlertes:

    @pytest.fixture
    def auth_pro(self, client):
        """Token d'un abonné Pro."""
        reg = client.post("/api/v1/auth/register", json={
            "email": f"pro_{uuid4().hex[:6]}@test.bf",
            "password": "motdepasse123",
            "prenom": "Pro", "nom": "User",
            "plan": "pro", "secteurs": [],
        })
        token = reg.json()["access_token"]
        # Simuler l'activation Pro (normalement via paiement)
        return {"Authorization": f"Bearer {token}"}

    def test_list_alertes_vide(self, client, auth_pro):
        resp = client.get("/api/v1/alertes", headers=auth_pro)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_alerte(self, client, auth_pro):
        resp = client.post("/api/v1/alertes", headers=auth_pro, json={
            "secteurs":  ["informatique", "btp"],
            "mots_cles": [],
            "sources":   [],
            "canal":     "les_deux",
            "rappel_j3": True,
        })
        assert resp.status_code in (201, 403)  # 403 si limite gratuite

    def test_toggle_alerte_inexistante(self, client, auth_pro):
        fake_id = str(uuid4())
        resp = client.post(f"/api/v1/alertes/{fake_id}/toggle", headers=auth_pro)
        assert resp.status_code == 404


# ── Tests Favoris ─────────────────────────────────────────────────────────────

class TestFavoris:

    @pytest.fixture
    def auth_headers(self, client):
        reg = client.post("/api/v1/auth/register", json={
            "email": f"fav_{uuid4().hex[:6]}@test.bf",
            "password": "motdepasse123",
            "prenom": "Fav", "nom": "User",
            "plan": "gratuit", "secteurs": [],
        })
        token = reg.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_list_favoris_vide(self, client, auth_headers):
        resp = client.get("/api/v1/favoris", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_add_favori_ao_inexistant(self, client, auth_headers):
        resp = client.post("/api/v1/favoris", headers=auth_headers,
                           json={"ao_id": str(uuid4())})
        assert resp.status_code == 404


# ── Tests Paiements ───────────────────────────────────────────────────────────

class TestPaiements:

    @pytest.fixture
    def auth_headers(self, client):
        reg = client.post("/api/v1/auth/register", json={
            "email": f"pay_{uuid4().hex[:6]}@test.bf",
            "password": "motdepasse123",
            "prenom": "Pay", "nom": "User",
            "plan": "gratuit", "secteurs": [],
        })
        token = reg.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_initier_paiement_plan_invalide(self, client, auth_headers):
        resp = client.post("/api/v1/paiements/initier", headers=auth_headers, json={
            "plan": "invalide", "periode": "mensuel", "methode": "om",
        })
        assert resp.status_code == 422

    def test_initier_paiement_pro_mensuel(self, client, auth_headers):
        resp = client.post("/api/v1/paiements/initier", headers=auth_headers, json={
            "plan": "pro", "periode": "mensuel", "methode": "om",
        })
        # 201 si CinetPay répond (simulation), ou 200
        assert resp.status_code in (200, 201)
        if resp.status_code in (200, 201):
            data = resp.json()
            assert data["montant"] == 15_000
            assert data["plan"] == "pro"

    def test_webhook_cinetpay_valide(self, client):
        resp = client.post("/api/v1/paiements/webhook", json={
            "cpm_trans_id": "NSG-FAKE-TXN",
            "cpm_result":   "00",
        })
        # 200 même si transaction inconnue (idempotence)
        assert resp.status_code == 200

    def test_historique_vide(self, client, auth_headers):
        resp = client.get("/api/v1/paiements/historique", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ── Tests Health ──────────────────────────────────────────────────────────────

class TestHealth:

    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "netsync-gov-api"
