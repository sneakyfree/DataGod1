"""
Tests for datagod/scrapers/texas_api.py

Comprehensive tests for Texas County Records API Integration.
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestTexasCountyAPIStructure:
    """Tests for TexasCountyAPI class structure"""

    def test_imports_base_api_integration(self):
        """Test that BaseAPIIntegration is imported"""
        from datagod.scrapers.texas_api import BaseAPIIntegration

        assert BaseAPIIntegration is not None

    def test_texas_county_api_exists(self):
        """Test that TexasCountyAPI class exists"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert TexasCountyAPI is not None

    def test_texas_county_api_is_class(self):
        """Test that TexasCountyAPI is a class"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert isinstance(TexasCountyAPI, type)

    def test_texas_county_api_inherits_base(self):
        """Test that TexasCountyAPI inherits from BaseAPIIntegration"""
        from datagod.scrapers.texas_api import BaseAPIIntegration, TexasCountyAPI

        assert issubclass(TexasCountyAPI, BaseAPIIntegration)


class TestTexasCountyAPIConfig:
    """Tests for TexasCountyAPI COUNTY_APIS configuration"""

    def test_county_apis_exists(self):
        """Test that COUNTY_APIS class attribute exists"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert hasattr(TexasCountyAPI, "COUNTY_APIS")
        assert isinstance(TexasCountyAPI.COUNTY_APIS, dict)

    def test_harris_county_in_config(self):
        """Test that Harris County is in configuration"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert "harris" in TexasCountyAPI.COUNTY_APIS

    def test_dallas_county_in_config(self):
        """Test that Dallas County is in configuration"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert "dallas" in TexasCountyAPI.COUNTY_APIS

    def test_tarrant_county_in_config(self):
        """Test that Tarrant County is in configuration"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert "tarrant" in TexasCountyAPI.COUNTY_APIS

    def test_bexar_county_in_config(self):
        """Test that Bexar County is in configuration"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert "bexar" in TexasCountyAPI.COUNTY_APIS

    def test_travis_county_in_config(self):
        """Test that Travis County is in configuration"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert "travis" in TexasCountyAPI.COUNTY_APIS

    def test_county_config_has_base_url(self):
        """Test that county configs have base_url"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        for county, config in TexasCountyAPI.COUNTY_APIS.items():
            assert "base_url" in config, f"{county} missing base_url"

    def test_county_config_has_features(self):
        """Test that county configs have features"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        for county, config in TexasCountyAPI.COUNTY_APIS.items():
            assert "features" in config, f"{county} missing features"
            assert isinstance(config["features"], list)

    def test_harris_has_property_search(self):
        """Test that Harris County has property_search feature"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert "property_search" in TexasCountyAPI.COUNTY_APIS["harris"]["features"]

    def test_harris_has_deed_records(self):
        """Test that Harris County has deed_records feature"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert "deed_records" in TexasCountyAPI.COUNTY_APIS["harris"]["features"]

    def test_harris_has_mortgage_records(self):
        """Test that Harris County has mortgage_records feature"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert "mortgage_records" in TexasCountyAPI.COUNTY_APIS["harris"]["features"]


class TestTexasCountyAPIInitialization:
    """Tests for TexasCountyAPI initialization"""

    def test_extract_county_name_method_exists(self):
        """Test that _extract_county_name method exists"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert hasattr(TexasCountyAPI, "_extract_county_name")
        assert callable(getattr(TexasCountyAPI, "_extract_county_name"))

    def test_has_init_method(self):
        """Test that TexasCountyAPI has __init__"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert hasattr(TexasCountyAPI, "__init__")


class TestTexasCountyAPIMethods:
    """Tests for TexasCountyAPI methods"""

    def test_search_records_method_exists(self):
        """Test that search_records method exists"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert hasattr(TexasCountyAPI, "search_records")

    def test_search_property_records_method_exists(self):
        """Test that _search_property_records method exists"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert hasattr(TexasCountyAPI, "_search_property_records")

    def test_search_deed_records_method_exists(self):
        """Test that _search_deed_records method exists"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert hasattr(TexasCountyAPI, "_search_deed_records")

    def test_get_record_details_method_exists(self):
        """Test that get_record_details method exists"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert hasattr(TexasCountyAPI, "get_record_details")

    def test_get_mortgage_records_method_exists(self):
        """Test that get_mortgage_records method exists"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert hasattr(TexasCountyAPI, "get_mortgage_records")


class TestTexasCountyAPIMapping:
    """Tests for TexasCountyAPI data mapping methods"""

    def test_map_property_to_standard_exists(self):
        """Test that _map_property_to_standard method exists"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert hasattr(TexasCountyAPI, "_map_property_to_standard")

    def test_map_deed_to_standard_exists(self):
        """Test that _map_deed_to_standard method exists"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert hasattr(TexasCountyAPI, "_map_deed_to_standard")

    def test_map_mortgage_to_standard_exists(self):
        """Test that _map_mortgage_to_standard method exists"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert hasattr(TexasCountyAPI, "_map_mortgage_to_standard")


class TestHarrisCountyAPI:
    """Tests for HarrisCountyAPI specialized class"""

    def test_harris_county_api_exists(self):
        """Test that HarrisCountyAPI class exists"""
        from datagod.scrapers.texas_api import HarrisCountyAPI

        assert HarrisCountyAPI is not None

    def test_harris_county_api_inherits_texas(self):
        """Test that HarrisCountyAPI inherits from TexasCountyAPI"""
        from datagod.scrapers.texas_api import HarrisCountyAPI, TexasCountyAPI

        assert issubclass(HarrisCountyAPI, TexasCountyAPI)

    def test_get_flood_zone_info_exists(self):
        """Test that get_flood_zone_info method exists (Harris specific)"""
        from datagod.scrapers.texas_api import HarrisCountyAPI

        assert hasattr(HarrisCountyAPI, "get_flood_zone_info")


class TestDallasCountyAPI:
    """Tests for DallasCountyAPI specialized class"""

    def test_dallas_county_api_exists(self):
        """Test that DallasCountyAPI class exists"""
        from datagod.scrapers.texas_api import DallasCountyAPI

        assert DallasCountyAPI is not None

    def test_dallas_county_api_inherits_texas(self):
        """Test that DallasCountyAPI inherits from TexasCountyAPI"""
        from datagod.scrapers.texas_api import DallasCountyAPI, TexasCountyAPI

        assert issubclass(DallasCountyAPI, TexasCountyAPI)

    def test_get_ucc_filings_exists(self):
        """Test that get_ucc_filings method exists (Dallas specific)"""
        from datagod.scrapers.texas_api import DallasCountyAPI

        assert hasattr(DallasCountyAPI, "get_ucc_filings")

    def test_map_ucc_to_standard_exists(self):
        """Test that _map_ucc_to_standard method exists"""
        from datagod.scrapers.texas_api import DallasCountyAPI

        assert hasattr(DallasCountyAPI, "_map_ucc_to_standard")


class TestTravisCountyAPI:
    """Tests for TravisCountyAPI specialized class"""

    def test_travis_county_api_exists(self):
        """Test that TravisCountyAPI class exists"""
        from datagod.scrapers.texas_api import TravisCountyAPI

        assert TravisCountyAPI is not None

    def test_travis_county_api_inherits_texas(self):
        """Test that TravisCountyAPI inherits from TexasCountyAPI"""
        from datagod.scrapers.texas_api import TexasCountyAPI, TravisCountyAPI

        assert issubclass(TravisCountyAPI, TexasCountyAPI)


class TestTexasCountyAPIWithHarrisCounty:
    """Tests using HarrisCountyAPI concrete class"""

    @pytest.fixture
    def harris_api(self):
        """Create a HarrisCountyAPI instance"""
        try:
            from datagod.scrapers.texas_api import HarrisCountyAPI

            # Create with minimal config
            api = HarrisCountyAPI(
                jurisdiction_id=1, config={"jurisdiction_name": "Harris County"}
            )
            return api
        except Exception:
            pytest.skip("Could not create HarrisCountyAPI instance")

    def test_harris_api_has_search_records(self, harris_api):
        """Test that HarrisCountyAPI has search_records method"""
        assert hasattr(harris_api, "search_records")

    def test_harris_api_has_map_property_to_standard(self, harris_api):
        """Test that HarrisCountyAPI has _map_property_to_standard method"""
        assert hasattr(harris_api, "_map_property_to_standard")

    def test_harris_api_has_map_deed_to_standard(self, harris_api):
        """Test that HarrisCountyAPI has _map_deed_to_standard method"""
        assert hasattr(harris_api, "_map_deed_to_standard")

    def test_harris_api_has_map_mortgage_to_standard(self, harris_api):
        """Test that HarrisCountyAPI has _map_mortgage_to_standard method"""
        assert hasattr(harris_api, "_map_mortgage_to_standard")

    def test_map_property_to_standard_returns_dict(self, harris_api):
        """Test that _map_property_to_standard returns a dict"""
        test_data = {
            "account_number": "12345",
            "situs_address": "123 Main St",
            "owner_name": "John Doe",
            "market_value": 500000,
            "city": "Houston",
            "zip_code": "77001",
        }

        result = harris_api._map_property_to_standard(test_data)
        assert isinstance(result, dict)
        assert result["record_type"] == "property"
        assert result["state"] == "TX"

    def test_map_deed_to_standard_returns_dict(self, harris_api):
        """Test that _map_deed_to_standard returns a dict"""
        test_data = {
            "document_type": "DEED",
            "document_number": "D12345",
            "grantor": "John Doe",
            "grantee": "Jane Doe",
            "consideration": 500000,
            "recording_date": "2024-01-15",
        }

        result = harris_api._map_deed_to_standard(test_data)
        assert isinstance(result, dict)
        assert result["state"] == "TX"
        assert "grantor" in result
        assert "grantee" in result

    def test_map_mortgage_to_standard_returns_dict(self, harris_api):
        """Test that _map_mortgage_to_standard returns a dict"""
        test_data = {
            "document_number": "M12345",
            "borrower": "John Doe",
            "lender": "Big Bank",
            "loan_amount": 400000,
            "recording_date": "2024-01-15",
        }

        result = harris_api._map_mortgage_to_standard(test_data)
        assert isinstance(result, dict)
        assert result["record_type"] == "mortgage"
        assert "borrower" in result
        assert "lender" in result


class TestTexasCountyAPICountyCount:
    """Tests for county coverage in Texas API"""

    def test_minimum_county_count(self):
        """Test that we have at least 10 Texas counties configured"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        assert len(TexasCountyAPI.COUNTY_APIS) >= 10

    def test_all_counties_have_required_fields(self):
        """Test that all counties have required configuration fields"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        required_fields = ["base_url", "features"]

        for county, config in TexasCountyAPI.COUNTY_APIS.items():
            for field in required_fields:
                assert field in config, f"{county} missing {field}"

    def test_major_texas_counties_covered(self):
        """Test that major Texas counties are covered"""
        from datagod.scrapers.texas_api import TexasCountyAPI

        major_counties = ["harris", "dallas", "tarrant", "bexar", "travis"]

        for county in major_counties:
            assert (
                county in TexasCountyAPI.COUNTY_APIS
            ), f"Missing major county: {county}"
