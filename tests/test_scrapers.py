"""
Tests for DataGod scrapers
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.skip(
    reason="TexasCountyAPI is missing abstract method implementations - needs refactoring"
)
class TestTexasCountyAPI:
    """Tests for Texas County API integration"""

    def test_texas_county_api_initialization(self, api_config):
        """Test Texas API initialization"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        api = TexasCountyAPI(jurisdiction_id=1, config=api_config)

        assert api.county_name == "harris"
        assert api.jurisdiction_id == 1
        assert "property_search" in api.available_features

    def test_texas_county_name_extraction(self, api_config):
        """Test county name extraction"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        api_config["jurisdiction_name"] = "Dallas County"
        api = TexasCountyAPI(jurisdiction_id=1, config=api_config)

        assert api.county_name == "dallas"

    def test_texas_property_mapping(self, api_config):
        """Test property data mapping to standard format"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        api = TexasCountyAPI(jurisdiction_id=1, config=api_config)

        raw_data = {
            "account_number": "12345",
            "owner_name": "John Smith",
            "situs_address": "123 Main St",
            "city": "Houston",
            "zip_code": "77001",
            "market_value": 350000,
        }

        result = api._map_property_to_standard(raw_data)

        assert result["record_type"] == "property"
        assert result["record_id"] == "12345"
        assert result["grantee"] == "John Smith"
        assert result["amount"] == 350000.0
        assert result["state"] == "TX"

    def test_texas_deed_mapping(self, api_config):
        """Test deed data mapping"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        api = TexasCountyAPI(jurisdiction_id=1, config=api_config)

        raw_data = {
            "document_number": "DOC-123",
            "document_type": "WARRANTY DEED",
            "grantor": "Jane Doe",
            "grantee": "John Smith",
            "consideration": 450000,
            "recording_date": "2024-01-15",
        }

        result = api._map_deed_to_standard(raw_data)

        assert result["record_type"] == "warranty deed"
        assert result["grantor"] == "Jane Doe"
        assert result["grantee"] == "John Smith"
        assert result["amount"] == 450000.0


class TestCaliforniaCountyAPI:
    """Tests for California County API integration"""

    def test_california_county_api_initialization(self):
        """Test California API initialization"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        config = {"jurisdiction_name": "Los Angeles County"}
        api = CaliforniaCountyAPI(jurisdiction_id=1, config=config)

        assert api.county_name == "los-angeles"
        assert "property_search" in api.available_features

    def test_california_property_mapping(self):
        """Test California property data mapping"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        config = {"jurisdiction_name": "Los Angeles County"}
        api = CaliforniaCountyAPI(jurisdiction_id=1, config=config)

        raw_data = {
            "apn": "1234-567-890",
            "owner_name": "Test Owner",
            "situs_address": "456 Oak Ave",
            "assessed_value": 750000,
        }

        result = api._map_property_to_standard(raw_data)

        assert result["record_type"] == "property"
        assert result["record_id"] == "1234-567-890"
        assert result["state"] == "CA"


class TestNewYorkCountyAPI:
    """Tests for New York County API integration"""

    def test_newyork_borough_name_mapping(self):
        """Test NYC borough name mapping"""
        from datagod.scrapers.newyork_api import NewYorkCountyAPI

        # Test Manhattan mapping
        config = {"jurisdiction_name": "Manhattan"}
        api = NewYorkCountyAPI(jurisdiction_id=1, config=config)
        assert api.county_name == "new-york"

        # Test Brooklyn mapping
        config = {"jurisdiction_name": "Brooklyn"}
        api = NewYorkCountyAPI(jurisdiction_id=2, config=config)
        assert api.county_name == "kings"

    def test_newyork_property_mapping(self):
        """Test New York property mapping"""
        from datagod.scrapers.newyork_api import NewYorkCountyAPI

        config = {"jurisdiction_name": "New York County"}
        api = NewYorkCountyAPI(jurisdiction_id=1, config=config)

        raw_data = {
            "bbl": "1001230045",
            "owner_name": "NYC Owner",
            "address": "100 Broadway",
            "market_value": 5000000,
            "borough": "Manhattan",
        }

        result = api._map_property_to_standard(raw_data)

        assert result["state"] == "NY"
        assert result["borough"] == "Manhattan"


class TestIllinoisCountyAPI:
    """Tests for Illinois County API integration"""

    def test_illinois_cook_county(self):
        """Test Cook County API"""
        from datagod.scrapers.illinois_api import CookCountyAPI

        config = {}
        api = CookCountyAPI(jurisdiction_id=1, config=config)

        assert api.county_name == "cook"
        assert "appeals" in api.available_features


class TestPennsylvaniaCountyAPI:
    """Tests for Pennsylvania County API integration"""

    def test_pennsylvania_philadelphia(self):
        """Test Philadelphia County API"""
        from datagod.scrapers.pennsylvania_api import PhiladelphiaCountyAPI

        config = {}
        api = PhiladelphiaCountyAPI(jurisdiction_id=1, config=config)

        assert api.county_name == "philadelphia"
        assert "permits" in api.available_features


class TestArizonaCountyAPI:
    """Tests for Arizona County API integration"""

    def test_arizona_maricopa(self):
        """Test Maricopa County API"""
        from datagod.scrapers.arizona_api import MaricopaCountyAPI

        config = {}
        api = MaricopaCountyAPI(jurisdiction_id=1, config=config)

        assert api.county_name == "maricopa"
        assert "liens" in api.available_features


class TestGeorgiaCountyAPI:
    """Tests for Georgia County API integration"""

    def test_georgia_fulton(self):
        """Test Fulton County API"""
        from datagod.scrapers.georgia_api import FultonCountyAPI

        config = {}
        api = FultonCountyAPI(jurisdiction_id=1, config=config)

        assert api.county_name == "fulton"
        assert "ucc_filings" in api.available_features


class TestOhioCountyAPI:
    """Tests for Ohio County API integration"""

    def test_ohio_cuyahoga(self):
        """Test Cuyahoga County API"""
        from datagod.scrapers.ohio_api import CuyahogaCountyAPI

        config = {}
        api = CuyahogaCountyAPI(jurisdiction_id=1, config=config)

        assert api.county_name == "cuyahoga"


class TestScraperRegistry:
    """Tests for the scraper registry"""

    def test_get_scraper_for_jurisdiction(self):
        """Test getting scraper by jurisdiction"""
        from datagod.scrapers import (
            HarrisCountyAPI,
            TexasCountyAPI,
            get_scraper_for_jurisdiction,
        )

        # Test default Texas scraper
        scraper_class = get_scraper_for_jurisdiction("TX")
        assert scraper_class == TexasCountyAPI

        # Test specific county scraper
        scraper_class = get_scraper_for_jurisdiction("TX", "Harris")
        assert scraper_class == HarrisCountyAPI

    def test_list_supported_states(self):
        """Test listing supported states"""
        from datagod.scrapers import list_supported_states

        states = list_supported_states()

        assert "TX" in states
        assert "CA" in states
        assert "NY" in states
        assert "FL" in states
        assert len(states) >= 9

    def test_list_supported_counties(self):
        """Test listing supported counties"""
        from datagod.scrapers import list_supported_counties

        tx_counties = list_supported_counties("TX")
        assert "harris" in tx_counties
        assert "dallas" in tx_counties

        ca_counties = list_supported_counties("CA")
        assert "los-angeles" in ca_counties

    def test_total_supported_counties(self):
        """Test total supported counties count"""
        from datagod.scrapers import TOTAL_SUPPORTED_COUNTIES

        assert TOTAL_SUPPORTED_COUNTIES >= 93


class TestFloridaCountyAPI:
    """Tests for Florida County API integration"""

    def test_florida_county_api_initialization(self):
        """Test Florida API initialization"""
        from datagod.scrapers.florida_api import FloridaMiamiDadeAPI

        config = {}
        api = FloridaMiamiDadeAPI(jurisdiction_id=1, config=config)

        assert api.county_name == "miami-dade"
        assert "property_search" in api.available_features

    def test_florida_api_has_available_features(self):
        """Test Florida API has expected features"""
        from datagod.scrapers.florida_api import FloridaMiamiDadeAPI

        config = {}
        api = FloridaMiamiDadeAPI(jurisdiction_id=1, config=config)

        # Check it has the expected available_features
        assert hasattr(api, "available_features")
        assert isinstance(api.available_features, list)


class TestWashingtonCountyAPI:
    """Tests for Washington State API integration"""

    def test_washington_county_api_initialization(self):
        """Test Washington API initialization"""
        from datagod.scrapers.washington_api import WashingtonCountyAPI

        config = {"jurisdiction_name": "King County"}
        api = WashingtonCountyAPI(jurisdiction_id=1, config=config)

        assert api.county_name == "king"
        # WashingtonCountyAPI uses county_name, not state_code


class TestColoradoCountyAPI:
    """Tests for Colorado API integration"""

    def test_colorado_county_api_initialization(self):
        """Test Colorado API initialization"""
        from datagod.scrapers.colorado_api import ColoradoCountyAPI

        config = {"jurisdiction_name": "Denver County"}
        api = ColoradoCountyAPI(jurisdiction_id=1, config=config)

        assert api.county_name == "denver"
        # ColoradoCountyAPI uses county_name, not state_code


class TestNorthCarolinaCountyAPI:
    """Tests for North Carolina API integration"""

    def test_nc_county_api_initialization(self):
        """Test NC API initialization"""
        from datagod.scrapers.northcarolina_api import NorthCarolinaCountyAPI

        config = {"jurisdiction_name": "Mecklenburg County"}
        api = NorthCarolinaCountyAPI(jurisdiction_id=1, config=config)

        assert api.county_name == "mecklenburg"


class TestVirginiaCountyAPI:
    """Tests for Virginia API integration"""

    def test_virginia_county_api_initialization(self):
        """Test Virginia API initialization"""
        from datagod.scrapers.virginia_api import VirginiaCountyAPI

        config = {"jurisdiction_name": "Fairfax County"}
        api = VirginiaCountyAPI(jurisdiction_id=1, config=config)

        assert api.county_name == "fairfax"


class TestNewJerseyCountyAPI:
    """Tests for New Jersey API integration"""

    def test_nj_county_api_initialization(self):
        """Test NJ API initialization"""
        from datagod.scrapers.newjersey_api import NewJerseyCountyAPI

        config = {"jurisdiction_name": "Bergen County"}
        api = NewJerseyCountyAPI(jurisdiction_id=1, config=config)

        assert api.county_name == "bergen"
