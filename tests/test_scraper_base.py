"""
Tests for scraper base classes and utilities
"""

import pytest
from unittest.mock import MagicMock, patch


class TestBaseScraper:
    """Tests for BaseScraper class"""

    def test_base_scraper_import(self):
        """Test BaseScraper can be imported"""
        from datagod.scrapers.base_scraper import BaseScraper
        assert BaseScraper is not None

    def test_base_scraper_has_required_methods(self):
        """Test BaseScraper has required interface methods"""
        from datagod.scrapers.base_scraper import BaseScraper
        assert hasattr(BaseScraper, 'scrape')


class TestScraperRegistry:
    """Tests for scraper registry in __init__"""

    def test_scrapers_init_import(self):
        """Test scrapers __init__ can be imported"""
        from datagod.scrapers import SUPPORTED_COUNTIES
        assert SUPPORTED_COUNTIES is not None

    def test_supported_counties_not_empty(self):
        """Test SUPPORTED_COUNTIES has entries"""
        from datagod.scrapers import SUPPORTED_COUNTIES
        assert len(SUPPORTED_COUNTIES) > 0

    def test_scraper_registry_import(self):
        """Test SCRAPER_REGISTRY can be imported"""
        from datagod.scrapers import SCRAPER_REGISTRY
        assert SCRAPER_REGISTRY is not None
        assert len(SCRAPER_REGISTRY) > 0

    def test_list_supported_states(self):
        """Test listing supported states"""
        from datagod.scrapers import list_supported_states
        states = list_supported_states()
        assert isinstance(states, list)
        assert len(states) > 0
        assert 'TX' in states
        assert 'CA' in states

    def test_list_supported_counties(self):
        """Test listing supported counties for a state"""
        from datagod.scrapers import list_supported_counties
        counties = list_supported_counties('TX')
        assert isinstance(counties, list)

    def test_get_scraper_for_jurisdiction(self):
        """Test getting scraper for a jurisdiction"""
        from datagod.scrapers import get_scraper_for_jurisdiction
        scraper = get_scraper_for_jurisdiction('TX')
        assert scraper is not None

    def test_get_scraper_for_invalid_state(self):
        """Test getting scraper for invalid state raises error"""
        from datagod.scrapers import get_scraper_for_jurisdiction
        with pytest.raises(ValueError):
            get_scraper_for_jurisdiction('XX')

    def test_get_scraper_for_specific_county(self):
        """Test getting scraper for specific county"""
        from datagod.scrapers import get_scraper_for_jurisdiction
        scraper = get_scraper_for_jurisdiction('TX', 'harris')
        assert scraper is not None

    def test_total_supported_counties(self):
        """Test TOTAL_SUPPORTED_COUNTIES value"""
        from datagod.scrapers import TOTAL_SUPPORTED_COUNTIES
        assert isinstance(TOTAL_SUPPORTED_COUNTIES, int)
        assert TOTAL_SUPPORTED_COUNTIES >= 0


class TestStateAPIIntegrations:
    """Tests for state API integration classes"""

    def test_florida_api_import(self):
        """Test Florida API can be imported"""
        from datagod.scrapers import FloridaPropertyAppraiserAPI
        assert FloridaPropertyAppraiserAPI is not None

    def test_texas_api_import(self):
        """Test Texas API can be imported"""
        from datagod.scrapers import TexasCountyAPI
        assert TexasCountyAPI is not None

    def test_california_api_import(self):
        """Test California API can be imported"""
        from datagod.scrapers import CaliforniaCountyAPI
        assert CaliforniaCountyAPI is not None

    def test_newyork_api_import(self):
        """Test New York API can be imported"""
        from datagod.scrapers import NewYorkCountyAPI
        assert NewYorkCountyAPI is not None

    def test_pennsylvania_api_import(self):
        """Test Pennsylvania API can be imported"""
        from datagod.scrapers import PennsylvaniaCountyAPI
        assert PennsylvaniaCountyAPI is not None

    def test_ohio_api_import(self):
        """Test Ohio API can be imported"""
        from datagod.scrapers import OhioCountyAPI
        assert OhioCountyAPI is not None

    def test_georgia_api_import(self):
        """Test Georgia API can be imported"""
        from datagod.scrapers import GeorgiaCountyAPI
        assert GeorgiaCountyAPI is not None

    def test_illinois_api_import(self):
        """Test Illinois API can be imported"""
        from datagod.scrapers import IllinoisCountyAPI
        assert IllinoisCountyAPI is not None

    def test_arizona_api_import(self):
        """Test Arizona API can be imported"""
        from datagod.scrapers import ArizonaCountyAPI
        assert ArizonaCountyAPI is not None

    def test_washington_api_import(self):
        """Test Washington API can be imported"""
        from datagod.scrapers import WashingtonCountyAPI
        assert WashingtonCountyAPI is not None

    def test_colorado_api_import(self):
        """Test Colorado API can be imported"""
        from datagod.scrapers import ColoradoCountyAPI
        assert ColoradoCountyAPI is not None

    def test_virginia_api_import(self):
        """Test Virginia API can be imported"""
        from datagod.scrapers import VirginiaCountyAPI
        assert VirginiaCountyAPI is not None

    def test_northcarolina_api_import(self):
        """Test North Carolina API can be imported"""
        from datagod.scrapers import NorthCarolinaCountyAPI
        assert NorthCarolinaCountyAPI is not None

    def test_newjersey_api_import(self):
        """Test New Jersey API can be imported"""
        from datagod.scrapers import NewJerseyCountyAPI
        assert NewJerseyCountyAPI is not None


class TestBaseAPIIntegration:
    """Tests for BaseAPIIntegration class"""

    def test_base_api_integration_import(self):
        """Test BaseAPIIntegration can be imported"""
        from datagod.scrapers import BaseAPIIntegration
        assert BaseAPIIntegration is not None

    def test_api_key_authentication_import(self):
        """Test APIKeyAuthentication can be imported"""
        from datagod.scrapers import APIKeyAuthentication
        assert APIKeyAuthentication is not None

    def test_oauth2_authentication_import(self):
        """Test OAuth2Authentication can be imported"""
        from datagod.scrapers import OAuth2Authentication
        assert OAuth2Authentication is not None

    def test_rate_limit_exceeded_import(self):
        """Test RateLimitExceeded can be imported"""
        from datagod.scrapers import RateLimitExceeded
        assert RateLimitExceeded is not None

    def test_api_auth_error_import(self):
        """Test APIAuthenticationError can be imported"""
        from datagod.scrapers import APIAuthenticationError
        assert APIAuthenticationError is not None

    def test_api_data_error_import(self):
        """Test APIDataError can be imported"""
        from datagod.scrapers import APIDataError
        assert APIDataError is not None


class TestCountySpecificAPIs:
    """Tests for county-specific API classes"""

    def test_harris_county_api_import(self):
        """Test Harris County API can be imported"""
        from datagod.scrapers import HarrisCountyAPI
        assert HarrisCountyAPI is not None

    def test_los_angeles_county_api_import(self):
        """Test Los Angeles County API can be imported"""
        from datagod.scrapers import LosAngelesCountyAPI
        assert LosAngelesCountyAPI is not None

    def test_cook_county_api_import(self):
        """Test Cook County API can be imported"""
        from datagod.scrapers import CookCountyAPI
        assert CookCountyAPI is not None

    def test_king_county_api_import(self):
        """Test King County API can be imported"""
        from datagod.scrapers import KingCountyAPI
        assert KingCountyAPI is not None

    def test_maricopa_county_api_import(self):
        """Test Maricopa County API can be imported"""
        from datagod.scrapers import MaricopaCountyAPI
        assert MaricopaCountyAPI is not None

    def test_denver_county_api_import(self):
        """Test Denver County API can be imported"""
        from datagod.scrapers import DenverCountyAPI
        assert DenverCountyAPI is not None
