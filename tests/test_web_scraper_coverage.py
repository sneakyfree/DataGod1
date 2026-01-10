"""
Tests for datagod/scrapers/web_scraper.py
Tests that actually import and exercise the module for real coverage.
"""
import pytest
import os
import json
import tempfile
import time
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime


class TestScraperConfig:
    """Test ScraperConfig dataclass"""

    def test_scraper_config_import(self):
        """Test that ScraperConfig can be imported"""
        from datagod.scrapers.web_scraper import ScraperConfig
        assert ScraperConfig is not None

    def test_scraper_config_creation(self):
        """Test creating a ScraperConfig"""
        from datagod.scrapers.web_scraper import ScraperConfig

        config = ScraperConfig(
            name="test_scraper",
            base_url="https://example.com",
            jurisdiction="Test County, XX",
            data_type="property"
        )

        assert config.name == "test_scraper"
        assert config.base_url == "https://example.com"
        assert config.jurisdiction == "Test County, XX"
        assert config.data_type == "property"

    def test_scraper_config_defaults(self):
        """Test ScraperConfig default values"""
        from datagod.scrapers.web_scraper import ScraperConfig

        config = ScraperConfig(
            name="test",
            base_url="https://test.com",
            jurisdiction="Test",
            data_type="property"
        )

        assert config.rate_limit == 5
        assert config.rate_limit_period == 60
        assert config.timeout == 30
        assert config.retry_count == 3
        assert config.retry_delay == 5
        assert "Mozilla" in config.user_agent

    def test_scraper_config_custom_values(self):
        """Test ScraperConfig with custom values"""
        from datagod.scrapers.web_scraper import ScraperConfig

        config = ScraperConfig(
            name="custom",
            base_url="https://custom.com",
            jurisdiction="Custom",
            data_type="deed",
            rate_limit=10,
            rate_limit_period=120,
            timeout=60,
            retry_count=5,
            retry_delay=10,
            user_agent="CustomBot/1.0"
        )

        assert config.rate_limit == 10
        assert config.rate_limit_period == 120
        assert config.timeout == 60
        assert config.retry_count == 5
        assert config.retry_delay == 10
        assert config.user_agent == "CustomBot/1.0"


class TestBaseWebScraper:
    """Test BaseWebScraper class"""

    def get_test_config(self):
        """Helper to create test config"""
        from datagod.scrapers.web_scraper import ScraperConfig
        return ScraperConfig(
            name="test_scraper",
            base_url="https://example.com",
            jurisdiction="Test County",
            data_type="property",
            rate_limit=5,
            rate_limit_period=1  # Short for testing
        )

    def test_base_web_scraper_init(self):
        """Test BaseWebScraper initialization"""
        from datagod.scrapers.web_scraper import BaseWebScraper, ScraperConfig

        config = self.get_test_config()
        scraper = BaseWebScraper(config)

        assert scraper.config == config
        assert scraper.session is not None
        assert scraper.last_request_time == 0
        assert scraper.request_count == 0

    def test_session_headers(self):
        """Test session headers are set correctly"""
        from datagod.scrapers.web_scraper import BaseWebScraper

        config = self.get_test_config()
        scraper = BaseWebScraper(config)

        assert "User-Agent" in scraper.session.headers
        assert "Accept" in scraper.session.headers
        assert "Accept-Language" in scraper.session.headers

    def test_close(self):
        """Test closing the scraper"""
        from datagod.scrapers.web_scraper import BaseWebScraper

        config = self.get_test_config()
        scraper = BaseWebScraper(config)
        scraper.close()
        # Should not raise an error

    def test_normalize_record(self):
        """Test record normalization"""
        from datagod.scrapers.web_scraper import BaseWebScraper

        config = self.get_test_config()
        scraper = BaseWebScraper(config)

        record = {
            "id": "123",
            "title": "Test Record",
            "description": "A test record",
            "amount": 1000.0,
            "date": "2024-01-01",
            "url": "https://example.com/123"
        }

        normalized = scraper.normalize_record(record)

        assert normalized["source"] == "test_scraper"
        assert normalized["source_id"] == "123"
        assert normalized["title"] == "Test Record"
        assert normalized["description"] == "A test record"
        assert normalized["amount"] == 1000.0
        assert normalized["date"] == "2024-01-01"
        assert normalized["url"] == "https://example.com/123"
        assert normalized["jurisdiction"] == "Test County"
        assert normalized["data_type"] == "property"
        assert "collected_at" in normalized
        assert normalized["scraper_version"] == "1.0"
        assert normalized["raw_data"] == record

    def test_normalize_record_missing_fields(self):
        """Test normalization with missing fields"""
        from datagod.scrapers.web_scraper import BaseWebScraper

        config = self.get_test_config()
        scraper = BaseWebScraper(config)

        record = {}  # Empty record

        normalized = scraper.normalize_record(record)

        assert "source_id" in normalized
        assert normalized["title"] == "Untitled Record"
        assert normalized["description"] == "No description available"
        assert normalized["url"] == ""


class TestRateLimiting:
    """Test rate limiting functionality"""

    def get_test_config(self, rate_limit=5, period=60):
        """Helper to create test config"""
        from datagod.scrapers.web_scraper import ScraperConfig
        return ScraperConfig(
            name="test",
            base_url="https://test.com",
            jurisdiction="Test",
            data_type="property",
            rate_limit=rate_limit,
            rate_limit_period=period
        )

    def test_check_rate_limit_first_request(self):
        """Test first request passes rate limit"""
        from datagod.scrapers.web_scraper import BaseWebScraper

        config = self.get_test_config()
        scraper = BaseWebScraper(config)

        scraper._check_rate_limit()
        assert scraper.request_count == 1

    def test_check_rate_limit_increments(self):
        """Test request count increments"""
        from datagod.scrapers.web_scraper import BaseWebScraper

        config = self.get_test_config()
        scraper = BaseWebScraper(config)

        for _ in range(3):
            scraper._check_rate_limit()

        assert scraper.request_count == 3

    def test_rate_limit_window_reset(self):
        """Test rate limit resets after window"""
        from datagod.scrapers.web_scraper import BaseWebScraper

        config = self.get_test_config(rate_limit=5, period=0.1)
        scraper = BaseWebScraper(config)

        for _ in range(5):
            scraper._check_rate_limit()
        assert scraper.request_count == 5

        # Wait for window to pass
        time.sleep(0.15)

        # Next request should reset
        scraper._check_rate_limit()
        assert scraper.request_count == 1


class TestMakeRequest:
    """Test _make_request method"""

    def get_test_config(self):
        """Helper to create test config"""
        from datagod.scrapers.web_scraper import ScraperConfig
        return ScraperConfig(
            name="test",
            base_url="https://test.com",
            jurisdiction="Test",
            data_type="property",
            rate_limit=100,
            rate_limit_period=60,
            retry_count=2,
            retry_delay=0.1
        )

    def test_make_request_success(self):
        """Test successful request"""
        from datagod.scrapers.web_scraper import BaseWebScraper

        config = self.get_test_config()
        scraper = BaseWebScraper(config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html>Success</html>"

        with patch.object(scraper.session, 'get', return_value=mock_response):
            result = scraper._make_request("https://example.com")

        assert result == "<html>Success</html>"

    def test_make_request_error_status(self):
        """Test request with error status code"""
        from datagod.scrapers.web_scraper import BaseWebScraper

        config = self.get_test_config()
        scraper = BaseWebScraper(config)

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        with patch.object(scraper.session, 'get', return_value=mock_response):
            result = scraper._make_request("https://example.com/notfound")

        assert result is None

    def test_make_request_rate_limited(self):
        """Test handling 429 rate limit response"""
        from datagod.scrapers.web_scraper import BaseWebScraper

        config = self.get_test_config()
        scraper = BaseWebScraper(config)

        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "0"}

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.text = "Success"

        # First returns 429, second returns 200
        with patch.object(scraper.session, 'get', side_effect=[mock_response_429, mock_response_200]):
            result = scraper._make_request("https://example.com")

        assert result == "Success"

    def test_make_request_exception(self):
        """Test request exception handling"""
        from datagod.scrapers.web_scraper import BaseWebScraper
        import requests

        config = self.get_test_config()
        scraper = BaseWebScraper(config)

        with patch.object(scraper.session, 'get', side_effect=requests.exceptions.Timeout("Timeout")):
            result = scraper._make_request("https://example.com")

        assert result is None


class TestGetSoup:
    """Test _get_soup method"""

    def get_test_config(self):
        """Helper to create test config"""
        from datagod.scrapers.web_scraper import ScraperConfig
        return ScraperConfig(
            name="test",
            base_url="https://test.com",
            jurisdiction="Test",
            data_type="property"
        )

    def test_get_soup_success(self):
        """Test getting BeautifulSoup from successful request"""
        from datagod.scrapers.web_scraper import BaseWebScraper
        from bs4 import BeautifulSoup

        config = self.get_test_config()
        scraper = BaseWebScraper(config)

        html = "<html><body><h1>Test</h1></body></html>"

        with patch.object(scraper, '_make_request', return_value=html):
            soup = scraper._get_soup("https://example.com")

        assert soup is not None
        assert isinstance(soup, BeautifulSoup)
        assert soup.h1.text == "Test"

    def test_get_soup_failed_request(self):
        """Test _get_soup when request fails"""
        from datagod.scrapers.web_scraper import BaseWebScraper

        config = self.get_test_config()
        scraper = BaseWebScraper(config)

        with patch.object(scraper, '_make_request', return_value=None):
            soup = scraper._get_soup("https://example.com")

        assert soup is None


class TestWebScraperManager:
    """Test WebScraperManager class"""

    def test_manager_init(self):
        """Test manager initialization"""
        from datagod.scrapers.web_scraper import WebScraperManager

        with patch('os.makedirs'):
            manager = WebScraperManager()

        assert manager.scrapers == {}
        assert manager.base_dir == 'datagod/scrapers/data'

    def test_add_scraper(self):
        """Test adding a scraper"""
        from datagod.scrapers.web_scraper import WebScraperManager, BaseWebScraper, ScraperConfig

        with patch('os.makedirs'):
            manager = WebScraperManager()

        config = ScraperConfig(
            name="test",
            base_url="https://test.com",
            jurisdiction="Test",
            data_type="property"
        )
        scraper = BaseWebScraper(config)

        manager.add_scraper("test_scraper", scraper)

        assert "test_scraper" in manager.scrapers
        assert manager.scrapers["test_scraper"] == scraper

    def test_get_scraper_exists(self):
        """Test getting existing scraper"""
        from datagod.scrapers.web_scraper import WebScraperManager, BaseWebScraper, ScraperConfig

        with patch('os.makedirs'):
            manager = WebScraperManager()

        config = ScraperConfig(
            name="test",
            base_url="https://test.com",
            jurisdiction="Test",
            data_type="property"
        )
        scraper = BaseWebScraper(config)
        manager.add_scraper("my_scraper", scraper)

        result = manager.get_scraper("my_scraper")
        assert result == scraper

    def test_get_scraper_not_exists(self):
        """Test getting non-existent scraper"""
        from datagod.scrapers.web_scraper import WebScraperManager

        with patch('os.makedirs'):
            manager = WebScraperManager()

        result = manager.get_scraper("nonexistent")
        assert result is None


class TestMockWebScraper:
    """Test MockWebScraper class"""

    def test_mock_web_scraper_import(self):
        """Test MockWebScraper can be imported"""
        from datagod.scrapers.web_scraper import MockWebScraper
        assert MockWebScraper is not None

    def test_mock_scraper_scrape(self):
        """Test mock scraper scraping"""
        from datagod.scrapers.web_scraper import MockWebScraper, ScraperConfig

        config = ScraperConfig(
            name="mock",
            base_url="https://mock.com",
            jurisdiction="Mock",
            data_type="property"
        )

        scraper = MockWebScraper(config)
        records = scraper.scrape()

        assert len(records) == 10
        for i, record in enumerate(records, 1):
            assert record["id"] == f"mock_scrape_{i}"
            assert "title" in record
            assert "amount" in record
            assert "date" in record


class TestCaliforniaPropertyScraper:
    """Test CaliforniaPropertyScraper class"""

    def test_california_scraper_import(self):
        """Test CaliforniaPropertyScraper can be imported"""
        from datagod.scrapers.web_scraper import CaliforniaPropertyScraper
        assert CaliforniaPropertyScraper is not None

    def test_california_scraper_scrape(self):
        """Test California scraper scraping"""
        from datagod.scrapers.web_scraper import CaliforniaPropertyScraper, ScraperConfig

        config = ScraperConfig(
            name="california",
            base_url="https://ca.gov",
            jurisdiction="Los Angeles County, CA",
            data_type="property"
        )

        scraper = CaliforniaPropertyScraper(config)
        records = scraper.scrape()

        # 3 pages * 5 records = 15
        assert len(records) == 15
        assert all("county" in r for r in records)
        assert all("address" in r for r in records)
        assert all("owner" in r for r in records)

    def test_california_normalize_record(self):
        """Test California record normalization"""
        from datagod.scrapers.web_scraper import CaliforniaPropertyScraper, ScraperConfig

        config = ScraperConfig(
            name="california",
            base_url="https://ca.gov",
            jurisdiction="Los Angeles County, CA",
            data_type="property"
        )

        scraper = CaliforniaPropertyScraper(config)
        record = {
            "id": "ca_123",
            "owner": "John Doe",
            "property_type": "Single Family Residence",
            "bedrooms": 3,
            "bathrooms": 2,
            "square_feet": 2000,
            "year_built": 2010
        }

        normalized = scraper.normalize_record(record)

        assert "additional_data" in normalized
        assert normalized["additional_data"]["owner"] == "John Doe"
        assert normalized["additional_data"]["property_type"] == "Single Family Residence"


class TestTexasPropertyScraper:
    """Test TexasPropertyScraper class"""

    def test_texas_scraper_import(self):
        """Test TexasPropertyScraper can be imported"""
        from datagod.scrapers.web_scraper import TexasPropertyScraper
        assert TexasPropertyScraper is not None

    def test_texas_scraper_scrape(self):
        """Test Texas scraper scraping"""
        from datagod.scrapers.web_scraper import TexasPropertyScraper, ScraperConfig

        config = ScraperConfig(
            name="texas",
            base_url="https://tx.gov",
            jurisdiction="Harris County, TX",
            data_type="property"
        )

        scraper = TexasPropertyScraper(config)
        records = scraper.scrape()

        assert len(records) == 15
        assert all("county" in r for r in records)

    def test_texas_normalize_record(self):
        """Test Texas record normalization"""
        from datagod.scrapers.web_scraper import TexasPropertyScraper, ScraperConfig

        config = ScraperConfig(
            name="texas",
            base_url="https://tx.gov",
            jurisdiction="Harris County, TX",
            data_type="property"
        )

        scraper = TexasPropertyScraper(config)
        record = {
            "id": "tx_123",
            "owner": "Jane Doe",
            "property_type": "Condominium",
            "bedrooms": 2,
            "bathrooms": 1,
            "square_feet": 1500,
            "year_built": 2015
        }

        normalized = scraper.normalize_record(record)

        assert "additional_data" in normalized


class TestFloridaPropertyScraper:
    """Test FloridaPropertyScraper class"""

    def test_florida_scraper_import(self):
        """Test FloridaPropertyScraper can be imported"""
        from datagod.scrapers.web_scraper import FloridaPropertyScraper
        assert FloridaPropertyScraper is not None

    def test_florida_scraper_scrape(self):
        """Test Florida scraper scraping"""
        from datagod.scrapers.web_scraper import FloridaPropertyScraper, ScraperConfig

        config = ScraperConfig(
            name="florida",
            base_url="https://fl.gov",
            jurisdiction="Miami-Dade County, FL",
            data_type="property"
        )

        scraper = FloridaPropertyScraper(config)
        records = scraper.scrape()

        assert len(records) == 15

    def test_florida_normalize_record(self):
        """Test Florida record normalization"""
        from datagod.scrapers.web_scraper import FloridaPropertyScraper, ScraperConfig

        config = ScraperConfig(
            name="florida",
            base_url="https://fl.gov",
            jurisdiction="Miami-Dade County, FL",
            data_type="property"
        )

        scraper = FloridaPropertyScraper(config)
        record = {
            "id": "fl_123",
            "owner": "Bob Smith",
            "property_type": "Vacation Home",
            "bedrooms": 4,
            "bathrooms": 3,
            "square_feet": 2500,
            "year_built": 2018
        }

        normalized = scraper.normalize_record(record)

        assert "additional_data" in normalized


class TestScraperManagerScrapeData:
    """Test WebScraperManager scrape_data method"""

    def test_scrape_data_success(self):
        """Test successful data scraping"""
        from datagod.scrapers.web_scraper import WebScraperManager, MockWebScraper, ScraperConfig

        with patch('os.makedirs'):
            manager = WebScraperManager()

        config = ScraperConfig(
            name="mock",
            base_url="https://mock.com",
            jurisdiction="Mock",
            data_type="property"
        )
        scraper = MockWebScraper(config)
        manager.add_scraper("mock", scraper)

        data = manager.scrape_data("mock")

        assert len(data) == 10
        assert all("source" in d for d in data)
        assert all(d["source"] == "mock" for d in data)

    def test_scrape_data_not_found(self):
        """Test scraping from non-existent scraper"""
        from datagod.scrapers.web_scraper import WebScraperManager

        with patch('os.makedirs'):
            manager = WebScraperManager()

        data = manager.scrape_data("nonexistent")
        assert data == []

    def test_scrape_data_exception(self):
        """Test scraping when exception occurs"""
        from datagod.scrapers.web_scraper import WebScraperManager, BaseWebScraper, ScraperConfig

        with patch('os.makedirs'):
            manager = WebScraperManager()

        config = ScraperConfig(
            name="error",
            base_url="https://error.com",
            jurisdiction="Error",
            data_type="property"
        )

        # Create scraper that raises exception
        scraper = MagicMock()
        scraper.scrape = MagicMock(side_effect=Exception("Scrape error"))

        manager.add_scraper("error", scraper)

        data = manager.scrape_data("error")
        assert data == []


class TestScraperManagerSaveData:
    """Test WebScraperManager save_scraper_data method"""

    def test_save_scraper_data(self):
        """Test saving scraped data"""
        from datagod.scrapers.web_scraper import WebScraperManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('os.makedirs'):
                manager = WebScraperManager()
                manager.base_dir = tmpdir

            data = [{"id": 1, "name": "Test"}]
            filepath = manager.save_scraper_data("test", data)

            assert os.path.exists(filepath)

            with open(filepath, 'r') as f:
                saved_data = json.load(f)

            assert saved_data == data

    def test_save_scraper_data_filename_format(self):
        """Test saved file has correct format"""
        from datagod.scrapers.web_scraper import WebScraperManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('os.makedirs'):
                manager = WebScraperManager()
                manager.base_dir = tmpdir

            filepath = manager.save_scraper_data("my_scraper", [])

            filename = os.path.basename(filepath)
            assert filename.startswith("my_scraper_scraped_data_")
            assert filename.endswith(".json")


class TestLogger:
    """Test logging configuration"""

    def test_logger_exists(self):
        """Test logger is configured"""
        from datagod.scrapers import web_scraper
        assert hasattr(web_scraper, 'logger')


class TestMainFunction:
    """Test main function"""

    def test_main_runs(self):
        """Test main function executes"""
        from datagod.scrapers.web_scraper import main

        with patch('os.makedirs'):
            with patch('builtins.print'):
                with patch('builtins.open', MagicMock()):
                    main()
