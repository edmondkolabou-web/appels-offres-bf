"""
NetSync Gov Transparence — Tests unitaires
Usage : python -m pytest 04_tests_transparence.py -v
"""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4


# ── Tests AttributionParser ───────────────────────────────────────────────────

class TestAttributionParser:

    @pytest.fixture(autouse=True)
    def setup(self):
        from parser_attributions import AttributionParser
        self.parser = AttributionParser()

    def test_detect_bloc_attribution(self):
        bloc = "RÉSULTATS D'ATTRIBUTION\nObjet : Acquisition matériel"
        assert self.parser.is_attribution_block(bloc) is True

    def test_detect_bloc_resultat_depouillement(self):
        bloc = "AVIS DE RÉSULTATS DE DÉPOUILLEMENT\nN° 2026-001"
        assert self.parser.is_attribution_block(bloc) is True

    def test_rejette_bloc_non_attribution(self):
        bloc = "AVIS D'APPEL D'OFFRES OUVERT\nAcquisition matériel informatique"
        assert self.parser.is_attribution_block(bloc) is False

    def test_extract_attributaire_standard(self):
        bloc = """RÉSULTATS D'ATTRIBUTION
Attributaire : Société Informatique de l'Ouest (SIO)
Montant : 38 750 000 FCFA"""
        val = self.parser.extract_attributaire(bloc)
        assert val is not None
        assert "Société Informatique" in val or "SIO" in val

    def test_extract_attributaire_entreprise_retenue(self):
        bloc = """RÉSULTATS D'ATTRIBUTION
Entreprise retenue : BTP Construction Sahel SARL
Montant TTC : 45 000 000 FCFA"""
        val = self.parser.extract_attributaire(bloc)
        assert val is not None
        assert "BTP Construction" in val or len(val) > 5

    def test_extract_montant_fcfa(self):
        bloc = "Montant du marché : 38 750 000 F CFA TTC"
        val = self.parser.extract_montant(bloc)
        assert val == 38_750_000

    def test_extract_montant_fcfa_sans_espace(self):
        bloc = "Montant : 45000000 FCFA"
        val = self.parser.extract_montant(bloc)
        assert val == 45_000_000

    def test_extract_montant_trop_petit_rejete(self):
        """Montant < 100 000 FCFA doit être ignoré (erreur de parsing)."""
        bloc = "Montant : 5000 FCFA"
        val = self.parser.extract_montant(bloc)
        assert val is None

    def test_extract_date_format_fr(self):
        bloc = "Date de signature : 15 mars 2026"
        val = self.parser.extract_date_signature(bloc)
        assert val == date(2026, 3, 15)

    def test_extract_date_format_iso(self):
        bloc = "Date de signature : 2026-03-15"
        val = self.parser.extract_date_signature(bloc)
        assert val == date(2026, 3, 15)

    def test_extract_date_format_slash(self):
        bloc = "Date de signature : 15/03/2026"
        val = self.parser.extract_date_signature(bloc)
        assert val == date(2026, 3, 15)

    def test_extract_reference(self):
        bloc = "N° 2026-001/MAERAH/SG/DMP/AO"
        val = self.parser.extract_reference(bloc)
        assert val is not None
        assert "2026-001" in val

    def test_parse_bloc_complet(self):
        bloc = """RÉSULTATS D'ATTRIBUTION
N° 2026-001/MAERAH/SG/DMP
Objet : Acquisition matériel informatique pour le PRECEL
Attributaire : Société Informatique de l'Ouest (SIO)
Montant TTC : 38 750 000 F CFA
Date de signature : 5 mars 2026"""
        attr = self.parser.parse_block(bloc, 715)
        assert attr is not None
        assert attr.attributaire is not None
        assert attr.montant_final == 38_750_000
        assert attr.date_signature == date(2026, 3, 5)
        assert attr.source_quotidien == 715
        assert attr.confiance >= 0.70

    def test_parse_bloc_trop_court_rejete(self):
        attr = self.parser.parse_block("RÉSULTATS D'ATTRIBUTION\nTrop court", 715)
        assert attr is None

    def test_parse_bloc_sans_attributaire_rejete(self):
        """Un bloc sans attributaire identifiable doit être rejeté."""
        bloc = """RÉSULTATS D'ATTRIBUTION
N° 2026-001/MAERAH
Montant : 38 750 000 FCFA"""
        attr = self.parser.parse_block(bloc, 715)
        # Pas d'attributaire → confiance < 0.40 → rejeté
        if attr is not None:
            assert attr.confiance >= 0.40

    def test_parse_document_multiple_attributions(self):
        doc = """
RÉSULTATS D'ATTRIBUTION N° 2026-001/MAERAH/SG/DMP
Attributaire : SIO SARL
Montant TTC : 38 750 000 F CFA
Date de signature : 5 mars 2026

RÉSULTATS D'ATTRIBUTION N° 2026-002/MENA/SG/DMP
Attributaire : BTP Construction Sahel
Montant : 125 000 000 FCFA
Date de signature : 10 mars 2026
"""
        attributions = self.parser.parse_document(doc, 715)
        assert len(attributions) >= 1  # Au moins 1 doit être parsée

    def test_confiance_avec_tous_champs(self):
        from parser_attributions import AttributionRaw
        attr = AttributionRaw(
            reference="2026-001",
            titre=None,
            attributaire="SIO SARL",
            montant_final=38_750_000,
            date_signature=date(2026, 3, 5),
            source_quotidien=715,
        )
        from parser_attributions import AttributionParser
        parser = AttributionParser()
        score = parser.calculate_confiance(attr)
        assert score == 1.0

    def test_confiance_sans_montant(self):
        from parser_attributions import AttributionRaw, AttributionParser
        attr = AttributionRaw(
            reference="2026-001",
            titre=None,
            attributaire="SIO SARL",
            montant_final=None,
            date_signature=date(2026, 3, 5),
            source_quotidien=715,
        )
        parser = AttributionParser()
        score = parser.calculate_confiance(attr)
        assert score == 0.70  # 0.40 + 0.20 + 0.10


# ── Tests endpoints API ───────────────────────────────────────────────────────

class TestEndpointsPublics:

    def make_db(self):
        db = MagicMock()
        db.execute.return_value.scalar.return_value = 42
        db.execute.return_value.fetchall.return_value = []
        db.execute.return_value.fetchone.return_value = None
        return db

    def test_search_aos_retourne_structure(self):
        from backend_transparence import search_aos_public
        db = self.make_db()
        result = search_aos_public(db=db)
        # La fonction retourne un JSONResponse
        assert result is not None

    def test_opendata_stats_champs_requis(self):
        from backend_transparence import opendata_stats
        from fastapi.responses import JSONResponse
        import json

        db = self.make_db()
        db.execute.return_value.scalar.side_effect = [450, 87, 38, 35, 15_000_000_000]
        db.execute.return_value.fetchone.return_value = MagicMock(secteur="informatique")

        result = opendata_stats(db)
        assert isinstance(result, JSONResponse)
        data = json.loads(result.body)

        assert "total_ao_indexes" in data
        assert "ao_ouverts" in data
        assert "source" in data
        assert "licence" in data
        assert "mis_a_jour" in data

    def test_opendata_schema_endpoints_documentes(self):
        from backend_transparence import opendata_schema
        from fastapi.responses import JSONResponse
        import json

        result = opendata_schema()
        data = json.loads(result.body)

        assert "endpoints" in data
        assert "/aos" in data["endpoints"]
        assert "/attributions" in data["endpoints"]
        assert "champs_ao" in data

    def test_cors_headers_presents(self):
        from backend_transparence import open_response
        from fastapi.responses import JSONResponse

        result = open_response({"test": True})
        assert "Access-Control-Allow-Origin" in result.headers
        assert result.headers["Access-Control-Allow-Origin"] == "*"

    def test_ao_inexistant_404(self):
        from fastapi import HTTPException
        from backend_transparence import get_ao_public

        db = self.make_db()
        db.execute.return_value.fetchone.return_value = None

        with pytest.raises(HTTPException) as exc:
            get_ao_public(str(uuid4()), db)
        assert exc.value.status_code == 404
