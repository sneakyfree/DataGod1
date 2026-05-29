"""
Tests for datagod/scrapers/generic_state_api.py

Comprehensive tests for the GenericStateAPI class and helper functions.
This module provides configuration-driven API integration for any state.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from datagod.scrapers.generic_state_api import (
    GenericStateAPI,
    GenericStateAPIError,
    get_state_api,
    list_configured_states,
    load_state_config,
)


class TestGenericStateAPIError:
    """Tests for the GenericStateAPIError exception class"""

    def test_error_can_be_raised(self):
        """Test that the error can be raised"""
        with pytest.raises(GenericStateAPIError) as exc_info:
            raise GenericStateAPIError("Test error message")
        assert "Test error message" in str(exc_info.value)

    def test_error_inherits_from_exception(self):
        """Test that error inherits from Exception"""
        error = GenericStateAPIError("test")
        assert isinstance(error, Exception)


class TestGenericStateAPIInit:
    """Tests for GenericStateAPI initialization"""

    def test_init_with_minimal_config(self):
        """Test initialization with minimal required config"""
        config = {"state_code": "TN", "state_name": "Tennessee"}
        api = GenericStateAPI(jurisdiction_id=1, config=config)

        assert api.state_code == "TN"
        assert api.state_name == "Tennessee"
        assert api.auth_type == "none"
        assert api.counties == {}
        assert api.data_sources == {}
        assert api.current_county is None

    def test_init_with_full_config(self):
        """Test initialization with full configuration"""
        config = {
            "state_code": "TN",
            "state_name": "Tennessee",
            "auth_type": "api_key",
            "base_url": "https://api.tn.gov",
            "requests_per_minute": 120,
            "requests_per_hour": 2000,
            "timeout": 60,
            "retry_attempts": 5,
            "retry_backoff": 2.0,
            "api_key": "test_key",
            "counties": [
                {"name": "Davidson", "base_url": "https://davidson.tn.gov/api"},
                {"name": "Knox", "base_url": "https://knox.tn.gov/api"},
            ],
            "data_sources": {
                "property": {"url": "/properties"},
                "deed": {"url": "/deeds"},
            },
        }
        api = GenericStateAPI(jurisdiction_id=1, config=config)

        assert api.state_code == "TN"
        assert api.state_name == "Tennessee"
        assert api.auth_type == "api_key"
        assert len(api.counties) == 2
        assert "davidson" in api.counties
        assert "knox" in api.counties
        assert "property" in api.data_sources
        assert "deed" in api.data_sources

    def test_init_with_oauth2_config(self):
        """Test initialization with OAuth2 configuration"""
        config = {
            "state_code": "CA",
            "state_name": "California",
            "auth_type": "oauth2",
            "token_url": "https://auth.ca.gov/token",
            "client_id": "client123",
            "client_secret": "secret456",
            "scope": "read:records",
        }
        api = GenericStateAPI(jurisdiction_id=1, config=config)

        assert api.auth_type == "oauth2"
        assert api.full_config["token_url"] == "https://auth.ca.gov/token"

    def test_init_missing_state_code_raises_error(self):
        """Test that missing state_code raises error"""
        config = {"state_name": "Tennessee"}
        with pytest.raises(GenericStateAPIError) as exc_info:
            GenericStateAPI(jurisdiction_id=1, config=config)
        assert "state_code" in str(exc_info.value)

    def test_init_missing_state_name_raises_error(self):
        """Test that missing state_name raises error"""
        config = {"state_code": "TN"}
        with pytest.raises(GenericStateAPIError) as exc_info:
            GenericStateAPI(jurisdiction_id=1, config=config)
        assert "state_name" in str(exc_info.value)

    def test_county_name_normalization(self):
        """Test that county names are normalized correctly"""
        config = {
            "state_code": "TN",
            "state_name": "Tennessee",
            "counties": [
                {"name": "O'Brien County"},
                {"name": "San Francisco County"},
            ],
        }
        api = GenericStateAPI(jurisdiction_id=1, config=config)

        assert "obrien_county" in api.counties
        assert "san_francisco_county" in api.counties


class TestGenericStateAPIAuthentication:
    """Tests for authentication methods"""

    def test_authenticate_no_auth(self):
        """Test authentication when no auth is required"""
        config = {"state_code": "TN", "state_name": "Tennessee", "auth_type": "none"}
        api = GenericStateAPI(jurisdiction_id=1, config=config)

        result = api.authenticate()
        assert result is True

    def test_authenticate_api_key_configured(self):
        """Test authentication with API key configured"""
        config = {
            "state_code": "TN",
            "state_name": "Tennessee",
            "auth_type": "api_key",
            "api_key": "test_api_key",
        }
        api = GenericStateAPI(jurisdiction_id=1, config=config)
        api.api_key = "test_api_key"

        result = api.authenticate()
        assert result is True

    def test_authenticate_api_key_not_configured(self):
        """Test authentication when API key not configured"""
        config = {"state_code": "TN", "state_name": "Tennessee", "auth_type": "api_key"}
        api = GenericStateAPI(jurisdiction_id=1, config=config)
        api.api_key = None

        result = api.authenticate()
        assert result is True  # Returns True even without key (allows attempts)

    def test_authenticate_hmac_configured(self):
        """Test HMAC authentication configured"""
        config = {
            "state_code": "TN",
            "state_name": "Tennessee",
            "auth_type": "hmac",
            "api_key": "key",
            "api_secret": "secret",
        }
        api = GenericStateAPI(jurisdiction_id=1, config=config)
        api.api_key = "key"
        api.api_secret = "secret"

        result = api.authenticate()
        assert result is True

    def test_authenticate_hmac_not_configured(self):
        """Test HMAC authentication without credentials"""
        config = {"state_code": "TN", "state_name": "Tennessee", "auth_type": "hmac"}
        api = GenericStateAPI(jurisdiction_id=1, config=config)
        api.api_key = None
        api.api_secret = None

        result = api.authenticate()
        assert result is True  # Returns True (allows attempts)

    def test_authenticate_unknown_auth_type(self):
        """Test authentication with unknown auth type"""
        config = {
            "state_code": "TN",
            "state_name": "Tennessee",
            "auth_type": "unknown_type",
        }
        api = GenericStateAPI(jurisdiction_id=1, config=config)

        result = api.authenticate()
        assert result is True

    @patch("requests.post")
    def test_oauth2_authenticate_success(self, mock_post):
        """Test successful OAuth2 authentication"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "token123",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        config = {
            "state_code": "CA",
            "state_name": "California",
            "auth_type": "oauth2",
            "token_url": "https://auth.ca.gov/token",
            "client_id": "client123",
            "client_secret": "secret456",
            "scope": "read:records",
        }
        api = GenericStateAPI(jurisdiction_id=1, config=config)

        result = api._oauth2_authenticate()

        assert result is True
        assert api.access_token == "token123"
        assert api.token_expires_at is not None

    @patch("requests.post")
    def test_oauth2_authenticate_failure(self, mock_post):
        """Test failed OAuth2 authentication"""
        mock_post.side_effect = Exception("Connection error")

        config = {
            "state_code": "CA",
            "state_name": "California",
            "auth_type": "oauth2",
            "token_url": "https://auth.ca.gov/token",
            "client_id": "client123",
            "client_secret": "secret456",
        }
        api = GenericStateAPI(jurisdiction_id=1, config=config)

        result = api._oauth2_authenticate()

        assert result is False

    def test_oauth2_authenticate_missing_credentials(self):
        """Test OAuth2 authentication with missing credentials"""
        config = {"state_code": "CA", "state_name": "California", "auth_type": "oauth2"}
        api = GenericStateAPI(jurisdiction_id=1, config=config)

        result = api._oauth2_authenticate()

        assert result is False


class TestGenericStateAPICountyManagement:
    """Tests for county management methods"""

    @pytest.fixture
    def api_with_counties(self):
        """Fixture for API with multiple counties"""
        config = {
            "state_code": "TN",
            "state_name": "Tennessee",
            "counties": [
                {"name": "Davidson", "base_url": "https://davidson.tn.gov/api"},
                {"name": "Knox", "base_url": "https://knox.tn.gov/api"},
                {"name": "Shelby", "property_endpoint": "/prop/search"},
            ],
        }
        return GenericStateAPI(jurisdiction_id=1, config=config)

    def test_set_county_valid(self, api_with_counties):
        """Test setting a valid county"""
        result = api_with_counties.set_county("Davidson")

        assert result is True
        assert api_with_counties.current_county == "davidson"
        assert api_with_counties.base_url == "https://davidson.tn.gov/api"

    def test_set_county_invalid(self, api_with_counties):
        """Test setting an invalid county"""
        result = api_with_counties.set_county("NonExistent")

        assert result is False
        assert api_with_counties.current_county is None

    def test_set_county_partial_match(self, api_with_counties):
        """Test setting county with partial match"""
        result = api_with_counties.set_county("David")  # Partial match

        assert result is True
        assert api_with_counties.current_county == "davidson"

    def test_set_county_case_insensitive(self, api_with_counties):
        """Test county matching is case insensitive"""
        result = api_with_counties.set_county("DAVIDSON")

        assert result is True
        assert api_with_counties.current_county == "davidson"

    def test_get_county_config_current(self, api_with_counties):
        """Test getting config for current county"""
        api_with_counties.set_county("Davidson")

        config = api_with_counties.get_county_config()

        assert config is not None
        assert config["name"] == "Davidson"
        assert config["base_url"] == "https://davidson.tn.gov/api"

    def test_get_county_config_by_name(self, api_with_counties):
        """Test getting config by county name"""
        config = api_with_counties.get_county_config("Knox")

        assert config is not None
        assert config["name"] == "Knox"

    def test_get_county_config_not_found(self, api_with_counties):
        """Test getting config for nonexistent county"""
        config = api_with_counties.get_county_config("NonExistent")

        assert config is None

    def test_list_counties(self, api_with_counties):
        """Test listing all counties"""
        counties = api_with_counties.list_counties()

        assert len(counties) == 3
        assert "Davidson" in counties
        assert "Knox" in counties
        assert "Shelby" in counties


class TestGenericStateAPISearch:
    """Tests for search methods"""

    @pytest.fixture
    def api_with_mock_request(self):
        """Fixture for API with mocked request method"""
        config = {
            "state_code": "TN",
            "state_name": "Tennessee",
            "counties": [
                {"name": "Davidson", "base_url": "https://davidson.tn.gov/api"},
            ],
        }
        api = GenericStateAPI(jurisdiction_id=1, config=config)
        api.set_county("Davidson")
        return api

    @patch.object(GenericStateAPI, "make_request")
    @patch.object(GenericStateAPI, "validate_response")
    def test_search_records_all_types(
        self, mock_validate, mock_request, api_with_mock_request
    ):
        """Test searching all record types"""
        mock_response = Mock()
        mock_request.return_value = mock_response
        mock_validate.return_value = {"results": []}

        query = {"name": "Smith"}
        results = api_with_mock_request.search_records(query)

        # Should call for property, deed, and lien
        assert mock_request.call_count == 3

    @patch.object(GenericStateAPI, "make_request")
    @patch.object(GenericStateAPI, "validate_response")
    def test_search_records_specific_type(
        self, mock_validate, mock_request, api_with_mock_request
    ):
        """Test searching specific record type"""
        mock_response = Mock()
        mock_request.return_value = mock_response
        mock_validate.return_value = {"results": []}

        query = {"name": "Smith", "record_type": "property"}
        results = api_with_mock_request.search_records(query)

        assert mock_request.call_count == 1

    @patch.object(GenericStateAPI, "make_request")
    @patch.object(GenericStateAPI, "validate_response")
    def test_search_records_with_county_kwarg(
        self, mock_validate, mock_request, api_with_mock_request
    ):
        """Test searching with county in kwargs"""
        mock_response = Mock()
        mock_request.return_value = mock_response
        mock_validate.return_value = {"results": []}

        query = {"name": "Smith", "record_type": "property"}
        results = api_with_mock_request.search_records(query, county="Davidson")

        assert api_with_mock_request.current_county == "davidson"

    @patch.object(GenericStateAPI, "make_request")
    @patch.object(GenericStateAPI, "validate_response")
    def test_search_endpoint_property(
        self, mock_validate, mock_request, api_with_mock_request
    ):
        """Test property search endpoint"""
        mock_response = Mock()
        mock_request.return_value = mock_response
        mock_validate.return_value = {
            "results": [{"id": "1", "owner_name": "Smith", "address": "123 Main St"}]
        }

        query = {"name": "Smith", "address": "123 Main St", "parcel_id": "ABC123"}
        results = api_with_mock_request._search_endpoint("property", query)

        assert len(results) == 1
        assert results[0]["record_type"] == "property"
        assert results[0]["source_county"] == "Davidson"

    @patch.object(GenericStateAPI, "make_request")
    @patch.object(GenericStateAPI, "validate_response")
    def test_search_endpoint_deed(
        self, mock_validate, mock_request, api_with_mock_request
    ):
        """Test deed search endpoint"""
        mock_response = Mock()
        mock_request.return_value = mock_response
        mock_validate.return_value = {
            "results": [{"id": "1", "party_name": "Smith", "doc_number": "D12345"}]
        }

        query = {
            "name": "Smith",
            "date_from": "2023-01-01",
            "date_to": "2023-12-31",
            "document_number": "D12345",
        }
        results = api_with_mock_request._search_endpoint("deed", query)

        assert len(results) == 1
        assert results[0]["record_type"] == "deed"

    @patch.object(GenericStateAPI, "make_request")
    @patch.object(GenericStateAPI, "validate_response")
    def test_search_endpoint_lien(
        self, mock_validate, mock_request, api_with_mock_request
    ):
        """Test lien search endpoint"""
        mock_response = Mock()
        mock_request.return_value = mock_response
        mock_validate.return_value = {
            "results": [{"id": "1", "debtor_name": "Smith", "amount": 50000}]
        }

        query = {"name": "Smith", "date_from": "2023-01-01", "date_to": "2023-12-31"}
        results = api_with_mock_request._search_endpoint("lien", query)

        assert len(results) == 1
        assert results[0]["record_type"] == "lien"

    def test_search_endpoint_no_county_configured(self, api_with_mock_request):
        """Test search when no county is configured"""
        api_with_mock_request.current_county = None

        results = api_with_mock_request._search_endpoint("property", {"name": "Smith"})

        assert results == []

    @patch.object(GenericStateAPI, "make_request")
    def test_search_endpoint_api_error(self, mock_request, api_with_mock_request):
        """Test search when API returns error"""
        from datagod.scrapers.base_api_integration import APIDataError

        mock_request.side_effect = APIDataError("API Error")

        results = api_with_mock_request._search_endpoint("property", {"name": "Smith"})

        assert results == []

    @patch.object(GenericStateAPI, "make_request")
    def test_search_endpoint_rate_limit(self, mock_request, api_with_mock_request):
        """Test search when rate limited"""
        from datagod.scrapers.base_api_integration import RateLimitExceeded

        mock_request.side_effect = RateLimitExceeded("Rate limited")

        results = api_with_mock_request._search_endpoint("property", {"name": "Smith"})

        assert results == []

    @patch.object(GenericStateAPI, "make_request")
    def test_search_endpoint_unexpected_error(
        self, mock_request, api_with_mock_request
    ):
        """Test search with unexpected error"""
        mock_request.side_effect = Exception("Unexpected error")

        results = api_with_mock_request._search_endpoint("property", {"name": "Smith"})

        assert results == []


class TestGenericStateAPIBuildSearchParams:
    """Tests for _build_search_params method"""

    @pytest.fixture
    def api(self):
        """Fixture for basic API"""
        config = {"state_code": "TN", "state_name": "Tennessee"}
        return GenericStateAPI(jurisdiction_id=1, config=config)

    def test_build_property_params(self, api):
        """Test building property search parameters"""
        query = {"name": "Smith", "address": "123 Main St", "parcel_id": "ABC123"}

        params = api._build_search_params("property", query)

        assert params["owner_name"] == "Smith"
        assert params["property_address"] == "123 Main St"
        assert params["parcel_number"] == "ABC123"

    def test_build_deed_params(self, api):
        """Test building deed search parameters"""
        query = {
            "name": "Smith",
            "date_from": "2023-01-01",
            "date_to": "2023-12-31",
            "document_number": "D12345",
        }

        params = api._build_search_params("deed", query)

        assert params["party_name"] == "Smith"
        assert params["start_date"] == "2023-01-01"
        assert params["end_date"] == "2023-12-31"
        assert params["doc_number"] == "D12345"

    def test_build_lien_params(self, api):
        """Test building lien search parameters"""
        query = {"name": "Smith", "date_from": "2023-01-01", "date_to": "2023-12-31"}

        params = api._build_search_params("lien", query)

        assert params["debtor_name"] == "Smith"
        assert params["filed_from"] == "2023-01-01"
        assert params["filed_to"] == "2023-12-31"

    def test_build_params_with_extra_fields(self, api):
        """Test that extra query fields are passed through"""
        query = {
            "name": "Smith",
            "custom_field": "custom_value",
            "another_field": "another_value",
        }

        params = api._build_search_params("property", query)

        assert params["custom_field"] == "custom_value"
        assert params["another_field"] == "another_value"

    def test_build_params_skips_empty_values(self, api):
        """Test that empty values are skipped"""
        query = {"name": "Smith", "address": None, "parcel_id": ""}

        params = api._build_search_params("property", query)

        assert "property_address" not in params


class TestGenericStateAPIRecordDetails:
    """Tests for get_record_details method"""

    @pytest.fixture
    def api_with_county(self):
        """Fixture for API with county set"""
        config = {
            "state_code": "TN",
            "state_name": "Tennessee",
            "counties": [{"name": "Davidson"}],
        }
        api = GenericStateAPI(jurisdiction_id=1, config=config)
        api.set_county("Davidson")
        return api

    @patch.object(GenericStateAPI, "make_request")
    @patch.object(GenericStateAPI, "validate_response")
    def test_get_record_details_success(
        self, mock_validate, mock_request, api_with_county
    ):
        """Test successful record details retrieval"""
        mock_response = Mock()
        mock_request.return_value = mock_response
        mock_validate.return_value = {
            "id": "REC123",
            "document_number": "D12345",
            "record_date": "2023-05-15",
        }

        result = api_with_county.get_record_details("REC123")

        assert result["record_id"] == "REC123"
        assert result["document_number"] == "D12345"

    def test_get_record_details_no_county(self, api_with_county):
        """Test getting details when no county set"""
        api_with_county.current_county = None

        result = api_with_county.get_record_details("REC123")

        assert result == {}

    @patch.object(GenericStateAPI, "make_request")
    def test_get_record_details_error(self, mock_request, api_with_county):
        """Test getting details when error occurs"""
        mock_request.side_effect = Exception("Error fetching details")

        result = api_with_county.get_record_details("REC123")

        assert result == {}


class TestGenericStateAPIDataMapping:
    """Tests for map_api_data_to_standard_format method"""

    @pytest.fixture
    def api(self):
        """Fixture for basic API"""
        config = {"state_code": "TN", "state_name": "Tennessee"}
        return GenericStateAPI(jurisdiction_id=1, config=config)

    def test_map_standard_fields(self, api):
        """Test mapping standard fields"""
        api_data = {
            "id": "REC123",
            "document_number": "D12345",
            "record_date": "2023-05-15",
            "document_type": "Deed",
            "grantor": "John Smith",
            "grantee": "Jane Doe",
            "address": "123 Main St",
            "parcel_id": "ABC123",
            "amount": 150000.00,
        }

        result = api.map_api_data_to_standard_format(api_data)

        assert result["source_state"] == "TN"
        assert result["source_api"] == "GenericStateAPI:TN"
        assert result["record_id"] == "REC123"
        assert result["document_number"] == "D12345"
        assert result["record_date"] == "2023-05-15"
        assert result["grantor"] == "John Smith"
        assert result["grantee"] == "Jane Doe"
        assert result["property_address"] == "123 Main St"
        assert result["parcel_id"] == "ABC123"
        assert result["amount"] == 150000.00
        assert result["raw_data"] == api_data
        assert "fetched_at" in result

    def test_map_alternative_field_names(self, api):
        """Test mapping with alternative field names"""
        api_data = {
            "doc_id": "REC123",
            "instrument_number": "I12345",
            "filing_date": "2023-05-15",
            "seller": "John Smith",
            "buyer": "Jane Doe",
            "situs_address": "123 Main St",
            "apn": "ABC123",
            "consideration": "$150,000.00",
        }

        result = api.map_api_data_to_standard_format(api_data)

        assert result["record_id"] == "REC123"
        assert result["document_number"] == "I12345"
        assert result["record_date"] == "2023-05-15"
        assert result["grantor"] == "John Smith"
        assert result["grantee"] == "Jane Doe"
        assert result["property_address"] == "123 Main St"
        assert result["parcel_id"] == "ABC123"
        assert result["amount"] == 150000.00

    def test_map_amount_with_currency_format(self, api):
        """Test parsing amount with currency formatting"""
        api_data = {"amount": "$1,234,567.89"}

        result = api.map_api_data_to_standard_format(api_data)

        assert result["amount"] == 1234567.89

    def test_map_amount_invalid(self, api):
        """Test handling invalid amount"""
        api_data = {"amount": "invalid"}

        result = api.map_api_data_to_standard_format(api_data)

        assert result["amount"] == "invalid"  # Kept as-is when parsing fails

    def test_map_date_formats(self, api):
        """Test parsing various date formats"""
        test_cases = [
            ("2023-05-15", "2023-05-15"),
            ("05/15/2023", "2023-05-15"),
            ("20230515", "2023-05-15"),
            ("15-05-2023", "2023-05-15"),
        ]

        for input_date, expected in test_cases:
            api_data = {"record_date": input_date}
            result = api.map_api_data_to_standard_format(api_data)
            assert result["record_date"] == expected, f"Failed for input: {input_date}"

    def test_map_empty_data(self, api):
        """Test mapping empty data"""
        result = api.map_api_data_to_standard_format({})

        assert result["source_state"] == "TN"
        assert result["source_api"] == "GenericStateAPI:TN"
        assert result["raw_data"] == {}


class TestGenericStateAPIHelperMethods:
    """Tests for helper methods"""

    @pytest.fixture
    def api(self):
        """Fixture for basic API with counties"""
        config = {
            "state_code": "TN",
            "state_name": "Tennessee",
            "counties": [
                {"name": "Davidson"},
                {"name": "Knox"},
            ],
        }
        return GenericStateAPI(jurisdiction_id=1, config=config)

    def test_get_supported_record_types(self, api):
        """Test getting supported record types"""
        types = api.get_supported_record_types()

        assert "property" in types
        assert "deed" in types
        assert "lien" in types
        assert "mortgage" in types
        assert "tax" in types

    def test_get_state_info(self, api):
        """Test getting state info"""
        with patch.object(api, "get_metrics", return_value={"requests": 100}):
            info = api.get_state_info()

        assert info["state_code"] == "TN"
        assert info["state_name"] == "Tennessee"
        assert info["counties_supported"] == 2
        assert info["api_class"] == "GenericStateAPI"
        assert "counties" in info
        assert "record_types" in info
        assert "metrics" in info


class TestLoadStateConfig:
    """Tests for load_state_config function"""

    def test_load_config_from_custom_dir(self):
        """Test loading config from custom directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a config file
            config_data = {"state_code": "TN", "state_name": "Tennessee"}
            config_path = Path(tmpdir) / "tn.json"
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            config = load_state_config("TN", configs_dir=tmpdir)

            assert config["state_code"] == "TN"
            assert config["state_name"] == "Tennessee"

    def test_load_config_not_found(self):
        """Test loading config that doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError) as exc_info:
                load_state_config("XX", configs_dir=tmpdir)
            assert "XX" in str(exc_info.value)

    def test_load_config_invalid_json(self):
        """Test loading invalid JSON config"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create invalid config file
            config_path = Path(tmpdir) / "tn.json"
            with open(config_path, "w") as f:
                f.write("not valid json")

            with pytest.raises(json.JSONDecodeError):
                load_state_config("TN", configs_dir=tmpdir)


class TestGetStateAPI:
    """Tests for get_state_api function"""

    def test_get_state_api_with_config(self):
        """Test getting API with provided config"""
        config = {"state_code": "TN", "state_name": "Tennessee"}

        api = get_state_api("TN", jurisdiction_id=1, config=config)

        assert isinstance(api, GenericStateAPI)
        assert api.state_code == "TN"

    @patch("datagod.scrapers.generic_state_api.load_state_config")
    def test_get_state_api_loads_config(self, mock_load):
        """Test that get_state_api loads config when not provided"""
        mock_load.return_value = {"state_code": "TN", "state_name": "Tennessee"}

        api = get_state_api("TN", jurisdiction_id=1)

        mock_load.assert_called_once_with("TN")
        assert api.state_code == "TN"


class TestListConfiguredStates:
    """Tests for list_configured_states function"""

    def test_list_states_custom_dir(self):
        """Test listing states from custom directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some config files
            for state in ["tn", "ca", "ny"]:
                config_path = Path(tmpdir) / f"{state}.json"
                config_path.write_text("{}")

            states = list_configured_states(configs_dir=tmpdir)

            assert len(states) == 3
            assert "TN" in states
            assert "CA" in states
            assert "NY" in states
            assert states == sorted(states)  # Should be sorted

    def test_list_states_empty_dir(self):
        """Test listing states from empty directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            states = list_configured_states(configs_dir=tmpdir)

            assert states == []


class TestGenericStateAPIResponseHandling:
    """Tests for various response format handling"""

    @pytest.fixture
    def api_with_county(self):
        """Fixture for API with county set"""
        config = {
            "state_code": "TN",
            "state_name": "Tennessee",
            "counties": [{"name": "Davidson"}],
        }
        api = GenericStateAPI(jurisdiction_id=1, config=config)
        api.set_county("Davidson")
        return api

    @patch.object(GenericStateAPI, "make_request")
    @patch.object(GenericStateAPI, "validate_response")
    def test_handle_results_key(self, mock_validate, mock_request, api_with_county):
        """Test handling response with 'results' key"""
        mock_request.return_value = Mock()
        mock_validate.return_value = {"results": [{"id": "1"}, {"id": "2"}]}

        results = api_with_county._search_endpoint("property", {"name": "Smith"})

        assert len(results) == 2

    @patch.object(GenericStateAPI, "make_request")
    @patch.object(GenericStateAPI, "validate_response")
    def test_handle_record_type_key(self, mock_validate, mock_request, api_with_county):
        """Test handling response with record type key (e.g., 'propertys')"""
        mock_request.return_value = Mock()
        mock_validate.return_value = {"propertys": [{"id": "1"}]}

        results = api_with_county._search_endpoint("property", {"name": "Smith"})

        assert len(results) == 1

    @patch.object(GenericStateAPI, "make_request")
    @patch.object(GenericStateAPI, "validate_response")
    def test_handle_data_key(self, mock_validate, mock_request, api_with_county):
        """Test handling response with 'data' key"""
        mock_request.return_value = Mock()
        mock_validate.return_value = {"data": [{"id": "1"}]}

        results = api_with_county._search_endpoint("property", {"name": "Smith"})

        assert len(results) == 1

    @patch.object(GenericStateAPI, "make_request")
    @patch.object(GenericStateAPI, "validate_response")
    def test_handle_single_record_response(
        self, mock_validate, mock_request, api_with_county
    ):
        """Test handling response that is a single record dict"""
        mock_request.return_value = Mock()
        mock_validate.return_value = {
            "data": {"id": "1"}  # Single dict instead of list
        }

        results = api_with_county._search_endpoint("property", {"name": "Smith"})

        assert len(results) == 1
        assert results[0]["record_id"] == "1"
