"""
Tests for datagod/scrapers/california_api.py

Comprehensive tests for California County Records API Integration.
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestCaliforniaCountyAPIStructure:
    """Tests for CaliforniaCountyAPI class structure"""

    def test_imports_base_api_integration(self):
        """Test that BaseAPIIntegration is imported"""
        from datagod.scrapers.california_api import BaseAPIIntegration

        assert BaseAPIIntegration is not None

    def test_california_county_api_exists(self):
        """Test that CaliforniaCountyAPI class exists"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert CaliforniaCountyAPI is not None

    def test_california_county_api_is_class(self):
        """Test that CaliforniaCountyAPI is a class"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert isinstance(CaliforniaCountyAPI, type)

    def test_california_county_api_inherits_base(self):
        """Test that CaliforniaCountyAPI inherits from BaseAPIIntegration"""
        from datagod.scrapers.california_api import (
            BaseAPIIntegration,
            CaliforniaCountyAPI,
        )

        assert issubclass(CaliforniaCountyAPI, BaseAPIIntegration)


class TestCaliforniaCountyAPIConfig:
    """Tests for CaliforniaCountyAPI COUNTY_APIS configuration"""

    def test_county_apis_exists(self):
        """Test that COUNTY_APIS class attribute exists"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert hasattr(CaliforniaCountyAPI, "COUNTY_APIS")
        assert isinstance(CaliforniaCountyAPI.COUNTY_APIS, dict)

    def test_los_angeles_county_in_config(self):
        """Test that Los Angeles County is in configuration"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert "los-angeles" in CaliforniaCountyAPI.COUNTY_APIS

    def test_san_diego_county_in_config(self):
        """Test that San Diego County is in configuration"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert "san-diego" in CaliforniaCountyAPI.COUNTY_APIS

    def test_orange_county_in_config(self):
        """Test that Orange County is in configuration"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert "orange" in CaliforniaCountyAPI.COUNTY_APIS

    def test_santa_clara_county_in_config(self):
        """Test that Santa Clara County is in configuration"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert "santa-clara" in CaliforniaCountyAPI.COUNTY_APIS

    def test_san_francisco_county_in_config(self):
        """Test that San Francisco County is in configuration"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert "san-francisco" in CaliforniaCountyAPI.COUNTY_APIS

    def test_county_config_has_base_url(self):
        """Test that county configs have base_url"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        for county, config in CaliforniaCountyAPI.COUNTY_APIS.items():
            assert "base_url" in config, f"{county} missing base_url"

    def test_county_config_has_features(self):
        """Test that county configs have features"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        for county, config in CaliforniaCountyAPI.COUNTY_APIS.items():
            assert "features" in config, f"{county} missing features"
            assert isinstance(config["features"], list)

    def test_la_has_property_search(self):
        """Test that LA County has property_search feature"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert (
            "property_search"
            in CaliforniaCountyAPI.COUNTY_APIS["los-angeles"]["features"]
        )

    def test_la_has_deed_records(self):
        """Test that LA County has deed_records feature"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert (
            "deed_records" in CaliforniaCountyAPI.COUNTY_APIS["los-angeles"]["features"]
        )

    def test_la_has_mortgage_records(self):
        """Test that LA County has mortgage_records feature"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert (
            "mortgage_records"
            in CaliforniaCountyAPI.COUNTY_APIS["los-angeles"]["features"]
        )

    def test_la_has_assessor_maps(self):
        """Test that LA County has assessor_maps feature"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert (
            "assessor_maps"
            in CaliforniaCountyAPI.COUNTY_APIS["los-angeles"]["features"]
        )


class TestCaliforniaCountyAPIInitialization:
    """Tests for CaliforniaCountyAPI initialization"""

    def test_extract_county_name_method_exists(self):
        """Test that _extract_county_name method exists"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert hasattr(CaliforniaCountyAPI, "_extract_county_name")
        assert callable(getattr(CaliforniaCountyAPI, "_extract_county_name"))

    def test_authenticate_method_exists(self):
        """Test that authenticate method exists"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert hasattr(CaliforniaCountyAPI, "authenticate")


class TestCaliforniaCountyAPIMethods:
    """Tests for CaliforniaCountyAPI methods"""

    def test_search_records_method_exists(self):
        """Test that search_records method exists"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert hasattr(CaliforniaCountyAPI, "search_records")

    def test_search_property_records_method_exists(self):
        """Test that _search_property_records method exists"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert hasattr(CaliforniaCountyAPI, "_search_property_records")

    def test_search_deed_records_method_exists(self):
        """Test that _search_deed_records method exists"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert hasattr(CaliforniaCountyAPI, "_search_deed_records")

    def test_search_mortgage_records_method_exists(self):
        """Test that _search_mortgage_records method exists"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert hasattr(CaliforniaCountyAPI, "_search_mortgage_records")

    def test_get_record_details_method_exists(self):
        """Test that get_record_details method exists"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert hasattr(CaliforniaCountyAPI, "get_record_details")

    def test_get_prop_13_info_method_exists(self):
        """Test that get_prop_13_info method exists (CA specific)"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert hasattr(CaliforniaCountyAPI, "get_prop_13_info")

    def test_map_api_data_to_standard_format_exists(self):
        """Test that map_api_data_to_standard_format method exists"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert hasattr(CaliforniaCountyAPI, "map_api_data_to_standard_format")


class TestCaliforniaCountyAPIMapping:
    """Tests for CaliforniaCountyAPI data mapping methods"""

    def test_map_property_to_standard_exists(self):
        """Test that _map_property_to_standard method exists"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert hasattr(CaliforniaCountyAPI, "_map_property_to_standard")

    def test_map_deed_to_standard_exists(self):
        """Test that _map_deed_to_standard method exists"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert hasattr(CaliforniaCountyAPI, "_map_deed_to_standard")

    def test_map_mortgage_to_standard_exists(self):
        """Test that _map_mortgage_to_standard method exists"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert hasattr(CaliforniaCountyAPI, "_map_mortgage_to_standard")


class TestLosAngelesCountyAPI:
    """Tests for LosAngelesCountyAPI specialized class"""

    def test_la_county_api_exists(self):
        """Test that LosAngelesCountyAPI class exists"""
        from datagod.scrapers.california_api import LosAngelesCountyAPI

        assert LosAngelesCountyAPI is not None

    def test_la_county_api_inherits_california(self):
        """Test that LosAngelesCountyAPI inherits from CaliforniaCountyAPI"""
        from datagod.scrapers.california_api import (
            CaliforniaCountyAPI,
            LosAngelesCountyAPI,
        )

        assert issubclass(LosAngelesCountyAPI, CaliforniaCountyAPI)

    def test_get_assessor_map_exists(self):
        """Test that get_assessor_map method exists (LA specific)"""
        from datagod.scrapers.california_api import LosAngelesCountyAPI

        assert hasattr(LosAngelesCountyAPI, "get_assessor_map")


class TestSanDiegoCountyAPI:
    """Tests for SanDiegoCountyAPI specialized class"""

    def test_san_diego_county_api_exists(self):
        """Test that SanDiegoCountyAPI class exists"""
        from datagod.scrapers.california_api import SanDiegoCountyAPI

        assert SanDiegoCountyAPI is not None

    def test_san_diego_county_api_inherits_california(self):
        """Test that SanDiegoCountyAPI inherits from CaliforniaCountyAPI"""
        from datagod.scrapers.california_api import (
            CaliforniaCountyAPI,
            SanDiegoCountyAPI,
        )

        assert issubclass(SanDiegoCountyAPI, CaliforniaCountyAPI)


class TestSanFranciscoCountyAPI:
    """Tests for SanFranciscoCountyAPI specialized class"""

    def test_sf_county_api_exists(self):
        """Test that SanFranciscoCountyAPI class exists"""
        from datagod.scrapers.california_api import SanFranciscoCountyAPI

        assert SanFranciscoCountyAPI is not None

    def test_sf_county_api_inherits_california(self):
        """Test that SanFranciscoCountyAPI inherits from CaliforniaCountyAPI"""
        from datagod.scrapers.california_api import (
            CaliforniaCountyAPI,
            SanFranciscoCountyAPI,
        )

        assert issubclass(SanFranciscoCountyAPI, CaliforniaCountyAPI)

    def test_get_rent_control_info_exists(self):
        """Test that get_rent_control_info method exists (SF specific)"""
        from datagod.scrapers.california_api import SanFranciscoCountyAPI

        assert hasattr(SanFranciscoCountyAPI, "get_rent_control_info")


class TestSantaClaraCountyAPI:
    """Tests for SantaClaraCountyAPI specialized class"""

    def test_santa_clara_county_api_exists(self):
        """Test that SantaClaraCountyAPI class exists"""
        from datagod.scrapers.california_api import SantaClaraCountyAPI

        assert SantaClaraCountyAPI is not None

    def test_santa_clara_county_api_inherits_california(self):
        """Test that SantaClaraCountyAPI inherits from CaliforniaCountyAPI"""
        from datagod.scrapers.california_api import (
            CaliforniaCountyAPI,
            SantaClaraCountyAPI,
        )

        assert issubclass(SantaClaraCountyAPI, CaliforniaCountyAPI)


class TestCaliforniaSecretaryOfStateAPI:
    """Tests for CaliforniaSecretaryOfStateAPI class"""

    def test_sos_api_exists(self):
        """Test that CaliforniaSecretaryOfStateAPI class exists"""
        from datagod.scrapers.california_api import CaliforniaSecretaryOfStateAPI

        assert CaliforniaSecretaryOfStateAPI is not None

    def test_sos_api_inherits_base(self):
        """Test that CaliforniaSecretaryOfStateAPI inherits from BaseAPIIntegration"""
        from datagod.scrapers.california_api import (
            BaseAPIIntegration,
            CaliforniaSecretaryOfStateAPI,
        )

        assert issubclass(CaliforniaSecretaryOfStateAPI, BaseAPIIntegration)

    def test_sos_search_records_exists(self):
        """Test that search_records method exists"""
        from datagod.scrapers.california_api import CaliforniaSecretaryOfStateAPI

        assert hasattr(CaliforniaSecretaryOfStateAPI, "search_records")

    def test_sos_get_record_details_exists(self):
        """Test that get_record_details method exists"""
        from datagod.scrapers.california_api import CaliforniaSecretaryOfStateAPI

        assert hasattr(CaliforniaSecretaryOfStateAPI, "get_record_details")

    def test_sos_search_businesses_exists(self):
        """Test that _search_businesses method exists"""
        from datagod.scrapers.california_api import CaliforniaSecretaryOfStateAPI

        assert hasattr(CaliforniaSecretaryOfStateAPI, "_search_businesses")

    def test_sos_search_liens_exists(self):
        """Test that _search_liens method exists"""
        from datagod.scrapers.california_api import CaliforniaSecretaryOfStateAPI

        assert hasattr(CaliforniaSecretaryOfStateAPI, "_search_liens")

    def test_sos_map_business_to_standard_exists(self):
        """Test that _map_business_to_standard_format method exists"""
        from datagod.scrapers.california_api import CaliforniaSecretaryOfStateAPI

        assert hasattr(
            CaliforniaSecretaryOfStateAPI, "_map_business_to_standard_format"
        )

    def test_sos_map_lien_to_standard_exists(self):
        """Test that _map_lien_to_standard_format method exists"""
        from datagod.scrapers.california_api import CaliforniaSecretaryOfStateAPI

        assert hasattr(CaliforniaSecretaryOfStateAPI, "_map_lien_to_standard_format")


class TestCaliforniaCountyAPIWithMocks:
    """Tests for CaliforniaCountyAPI with mocked dependencies"""

    @pytest.fixture
    def mock_api(self):
        """Create a mock CaliforniaCountyAPI instance"""
        with patch(
            "datagod.scrapers.california_api.BaseAPIIntegration.__init__",
            return_value=None,
        ):
            from datagod.scrapers.california_api import CaliforniaCountyAPI

            api = object.__new__(CaliforniaCountyAPI)
            api.jurisdiction_id = 1
            api.config = {"jurisdiction_name": "Los Angeles County"}
            api.metrics = Mock()
            api.request_timestamps = []
            api.session = Mock()
            api.base_url = "https://portal.assessor.lacounty.gov/api"
            api.recorder_url = "https://www.lavote.net/api/recorder"
            api.api_key = None
            api.api_secret = None
            api.access_token = None
            api.token_expires_at = None
            api.timeout = 30
            api.retry_attempts = 3
            api.retry_backoff = 1.0
            api.requests_per_minute = 60
            api.requests_per_hour = 1000
            api.county_name = "los-angeles"
            api.county_config = CaliforniaCountyAPI.COUNTY_APIS.get("los-angeles", {})
            api.available_features = [
                "property_search",
                "deed_records",
                "mortgage_records",
                "tax_info",
                "assessor_maps",
            ]

            return api

    def test_search_records_returns_list(self, mock_api):
        """Test that search_records returns a list"""
        mock_api._search_property_records = Mock(return_value=[])
        mock_api._search_deed_records = Mock(return_value=[])
        mock_api._search_mortgage_records = Mock(return_value=[])

        result = mock_api.search_records({})
        assert isinstance(result, list)

    def test_search_records_calls_property_search(self, mock_api):
        """Test that search_records calls property search when feature available"""
        mock_api._search_property_records = Mock(return_value=[])
        mock_api._search_deed_records = Mock(return_value=[])
        mock_api._search_mortgage_records = Mock(return_value=[])

        mock_api.search_records({})
        mock_api._search_property_records.assert_called_once()

    def test_authenticate_returns_true(self, mock_api):
        """Test that authenticate returns True"""
        result = mock_api.authenticate()
        assert result is True

    def test_map_property_to_standard_returns_dict(self, mock_api):
        """Test that _map_property_to_standard returns a dict"""
        test_data = {
            "apn": "1234-567-890",
            "situs_address": "123 Main St",
            "owner_name": "John Doe",
            "assessed_value": 500000,
            "city": "Los Angeles",
            "zip_code": "90001",
        }

        result = mock_api._map_property_to_standard(test_data)
        assert isinstance(result, dict)
        assert result["record_type"] == "property"
        assert result["state"] == "CA"
        assert "apn" in result

    def test_map_deed_to_standard_returns_dict(self, mock_api):
        """Test that _map_deed_to_standard returns a dict"""
        test_data = {
            "doc_type": "GRANT DEED",
            "document_number": "D12345",
            "grantor": "John Doe",
            "grantee": "Jane Doe",
            "transfer_tax": 550,
            "recording_date": "2024-01-15",
        }

        result = mock_api._map_deed_to_standard(test_data)
        assert isinstance(result, dict)
        assert result["state"] == "CA"
        assert "grantor" in result
        assert "grantee" in result

    def test_map_mortgage_to_standard_returns_dict(self, mock_api):
        """Test that _map_mortgage_to_standard returns a dict"""
        test_data = {
            "document_number": "M12345",
            "trustor": "John Doe",
            "beneficiary": "Big Bank",
            "trustee": "Title Company",
            "loan_amount": 400000,
            "recording_date": "2024-01-15",
        }

        result = mock_api._map_mortgage_to_standard(test_data)
        assert isinstance(result, dict)
        assert result["record_type"] == "mortgage"
        assert "borrower" in result or "trustor" in result["raw_data"]
        assert "lender" in result or "beneficiary" in result["raw_data"]


class TestCaliforniaCountyAPICountyCount:
    """Tests for county coverage in California API"""

    def test_minimum_county_count(self):
        """Test that we have at least 15 California counties configured"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        assert len(CaliforniaCountyAPI.COUNTY_APIS) >= 15

    def test_all_counties_have_required_fields(self):
        """Test that all counties have required configuration fields"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        required_fields = ["base_url", "features"]

        for county, config in CaliforniaCountyAPI.COUNTY_APIS.items():
            for field in required_fields:
                assert field in config, f"{county} missing {field}"

    def test_major_california_counties_covered(self):
        """Test that major California counties are covered"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        major_counties = [
            "los-angeles",
            "san-diego",
            "orange",
            "santa-clara",
            "san-francisco",
        ]

        for county in major_counties:
            assert (
                county in CaliforniaCountyAPI.COUNTY_APIS
            ), f"Missing major county: {county}"

    def test_bay_area_counties_covered(self):
        """Test that Bay Area counties are covered"""
        from datagod.scrapers.california_api import CaliforniaCountyAPI

        bay_area_counties = [
            "alameda",
            "santa-clara",
            "san-francisco",
            "san-mateo",
            "contra-costa",
        ]

        for county in bay_area_counties:
            assert (
                county in CaliforniaCountyAPI.COUNTY_APIS
            ), f"Missing Bay Area county: {county}"


class TestCaliforniaAPNFormat:
    """Tests for California APN (Assessor Parcel Number) handling"""

    @pytest.fixture
    def mock_api(self):
        """Create a mock CaliforniaCountyAPI instance"""
        with patch(
            "datagod.scrapers.california_api.BaseAPIIntegration.__init__",
            return_value=None,
        ):
            from datagod.scrapers.california_api import CaliforniaCountyAPI

            api = object.__new__(CaliforniaCountyAPI)
            api.jurisdiction_id = 1
            api.config = {}
            api.county_name = "los-angeles"
            api.available_features = ["property_search", "tax_info"]

            return api

    def test_map_property_includes_apn(self, mock_api):
        """Test that mapped property data includes APN"""
        test_data = {
            "apn": "1234-567-890",
            "situs_address": "123 Main St",
            "owner_name": "John Doe",
        }

        result = mock_api._map_property_to_standard(test_data)
        assert "apn" in result
        assert result["apn"] == "1234-567-890"

    def test_map_deed_includes_apn(self, mock_api):
        """Test that mapped deed data includes APN"""
        test_data = {
            "doc_type": "GRANT DEED",
            "document_number": "D12345",
            "grantor": "John Doe",
            "grantee": "Jane Doe",
            "apn": "1234-567-890",
        }

        result = mock_api._map_deed_to_standard(test_data)
        assert "apn" in result
        assert result["apn"] == "1234-567-890"
