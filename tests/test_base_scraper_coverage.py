"""
Tests for datagod/scrapers/base_scraper.py
Tests that actually import and exercise the module for real coverage.
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests


class TestBaseScraper:
    """Test BaseScraper class"""

    def test_base_scraper_import(self):
        """Test that BaseScraper can be imported"""
        from datagod.scrapers.base_scraper import BaseScraper

        assert BaseScraper is not None

    def test_base_scraper_is_abstract(self):
        """Test that BaseScraper is an abstract class"""
        from abc import ABC

        from datagod.scrapers.base_scraper import BaseScraper

        assert issubclass(BaseScraper, ABC)

    def test_concrete_scraper_creation(self):
        """Test creating a concrete implementation of BaseScraper"""
        from datagod.scrapers.base_scraper import BaseScraper

        class ConcreteScraper(BaseScraper):
            def scrape(self, **kwargs):
                return [{"test": "data"}]

        scraper = ConcreteScraper("https://example.com")
        assert scraper.base_url == "https://example.com"
        assert scraper.delay == 1.0
        assert scraper.timeout == 30

    def test_base_url_trailing_slash_removed(self):
        """Test that trailing slash is removed from base_url"""
        from datagod.scrapers.base_scraper import BaseScraper

        class ConcreteScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = ConcreteScraper("https://example.com/")
        assert scraper.base_url == "https://example.com"

    def test_custom_delay_and_timeout(self):
        """Test custom delay and timeout parameters"""
        from datagod.scrapers.base_scraper import BaseScraper

        class ConcreteScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = ConcreteScraper("https://example.com", delay=2.5, timeout=60)
        assert scraper.delay == 2.5
        assert scraper.timeout == 60

    def test_session_headers(self):
        """Test that session has proper headers set"""
        from datagod.scrapers.base_scraper import BaseScraper

        class ConcreteScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = ConcreteScraper("https://example.com")
        assert "User-Agent" in scraper.session.headers
        assert "DataGod-Scraper" in scraper.session.headers["User-Agent"]

    def test_scrape_method_returns_list(self):
        """Test that scrape method returns a list"""
        from datagod.scrapers.base_scraper import BaseScraper

        class ConcreteScraper(BaseScraper):
            def scrape(self, **kwargs):
                return [{"id": 1}, {"id": 2}]

        scraper = ConcreteScraper("https://example.com")
        result = scraper.scrape()
        assert isinstance(result, list)
        assert len(result) == 2


class TestMakeRequest:
    """Test _make_request method"""

    def get_concrete_scraper(self):
        """Helper to create a concrete scraper"""
        from datagod.scrapers.base_scraper import BaseScraper

        class ConcreteScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        return ConcreteScraper("https://example.com", delay=0)

    @patch("time.sleep")
    def test_make_request_get_success_json(self, mock_sleep):
        """Test successful GET request with JSON response"""
        scraper = self.get_concrete_scraper()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "value"}
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(scraper.session, "get", return_value=mock_response):
            result = scraper._make_request("https://example.com/api")

        assert result["success"] is True
        assert result["data"] == {"key": "value"}
        assert result["status_code"] == 200

    @patch("time.sleep")
    def test_make_request_get_success_text(self, mock_sleep):
        """Test successful GET request with text response"""
        scraper = self.get_concrete_scraper()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.text = "<html>content</html>"
        mock_response.raise_for_status = MagicMock()

        with patch.object(scraper.session, "get", return_value=mock_response):
            result = scraper._make_request("https://example.com/page")

        assert result["success"] is True
        assert result["data"] == "<html>content</html>"

    @patch("time.sleep")
    def test_make_request_post(self, mock_sleep):
        """Test POST request"""
        scraper = self.get_concrete_scraper()

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"created": True}
        mock_response.raise_for_status = MagicMock()

        with patch.object(scraper.session, "post", return_value=mock_response):
            result = scraper._make_request("https://example.com/api", method="POST")

        assert result["success"] is True
        assert result["status_code"] == 201

    @patch("time.sleep")
    def test_make_request_unsupported_method(self, mock_sleep):
        """Test unsupported HTTP method returns error dict"""
        scraper = self.get_concrete_scraper()

        # _make_request catches ValueError internally and returns error dict
        result = scraper._make_request("https://example.com", method="PATCH")
        assert result["success"] is False
        assert "Unsupported HTTP method" in result["error"]

    @patch("time.sleep")
    def test_make_request_request_exception(self, mock_sleep):
        """Test request exception handling"""
        scraper = self.get_concrete_scraper()

        with patch.object(
            scraper.session, "get", side_effect=requests.exceptions.Timeout("Timeout")
        ):
            result = scraper._make_request("https://example.com")

        assert result["success"] is False
        assert "Timeout" in result["error"]

    @patch("time.sleep")
    def test_make_request_http_error(self, mock_sleep):
        """Test HTTP error handling"""
        scraper = self.get_concrete_scraper()

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found"
        )

        with patch.object(scraper.session, "get", return_value=mock_response):
            result = scraper._make_request("https://example.com/notfound")

        assert result["success"] is False

    def test_make_request_respects_delay(self):
        """Test that delay is respected"""
        scraper = self.get_concrete_scraper()
        scraper.delay = 0.5

        with patch("time.sleep") as mock_sleep:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {}
            mock_response.raise_for_status = MagicMock()

            with patch.object(scraper.session, "get", return_value=mock_response):
                scraper._make_request("https://example.com")

            mock_sleep.assert_called_with(0.5)


class TestExtractLinks:
    """Test _extract_links method"""

    def get_concrete_scraper(self):
        """Helper to create a concrete scraper"""
        from datagod.scrapers.base_scraper import BaseScraper

        class ConcreteScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        return ConcreteScraper("https://example.com")

    def test_extract_absolute_links(self):
        """Test extracting absolute links"""
        scraper = self.get_concrete_scraper()
        html = """
        <html>
            <a href="https://example.com/page1">Page 1</a>
            <a href="https://example.com/page2">Page 2</a>
        </html>
        """
        links = scraper._extract_links(html, "https://example.com")
        assert "https://example.com/page1" in links
        assert "https://example.com/page2" in links

    def test_extract_relative_links_with_slash(self):
        """Test extracting relative links starting with /"""
        scraper = self.get_concrete_scraper()
        html = """
        <html>
            <a href="/page1">Page 1</a>
            <a href="/subdir/page2">Page 2</a>
        </html>
        """
        links = scraper._extract_links(html, "https://example.com")
        assert "https://example.com/page1" in links
        assert "https://example.com/subdir/page2" in links

    def test_extract_relative_links_without_slash(self):
        """Test extracting relative links without slash"""
        scraper = self.get_concrete_scraper()
        html = """
        <html>
            <a href="page1.html">Page 1</a>
        </html>
        """
        links = scraper._extract_links(html, "https://example.com")
        assert "https://example.com/page1.html" in links

    def test_extract_no_links(self):
        """Test HTML with no links"""
        scraper = self.get_concrete_scraper()
        html = "<html><body>No links here</body></html>"
        links = scraper._extract_links(html, "https://example.com")
        assert links == []


class TestParseJsonData:
    """Test _parse_json_data method"""

    def get_concrete_scraper(self):
        """Helper to create a concrete scraper"""
        from datagod.scrapers.base_scraper import BaseScraper

        class ConcreteScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        return ConcreteScraper("https://example.com")

    def test_parse_json_string(self):
        """Test parsing JSON string"""
        scraper = self.get_concrete_scraper()
        result = scraper._parse_json_data('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_dict(self):
        """Test parsing dict (passthrough)"""
        scraper = self.get_concrete_scraper()
        data = {"key": "value"}
        result = scraper._parse_json_data(data)
        assert result == data

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON string"""
        scraper = self.get_concrete_scraper()
        result = scraper._parse_json_data("not valid json")
        assert result == {}


class TestValidateData:
    """Test validate_data method"""

    def get_concrete_scraper(self):
        """Helper to create a concrete scraper"""
        from datagod.scrapers.base_scraper import BaseScraper

        class ConcreteScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        return ConcreteScraper("https://example.com")

    def test_validate_empty_data(self):
        """Test validating empty data"""
        scraper = self.get_concrete_scraper()
        assert scraper.validate_data({}) is False
        assert scraper.validate_data(None) is False

    def test_validate_missing_required_field(self):
        """Test validating data with missing required field"""
        scraper = self.get_concrete_scraper()
        data = {"source": "test", "scraped_at": "now"}  # missing 'data'
        assert scraper.validate_data(data) is False

    def test_validate_valid_data(self):
        """Test validating valid data"""
        scraper = self.get_concrete_scraper()
        data = {"source": "test", "scraped_at": "2024-01-01", "data": {"key": "value"}}
        assert scraper.validate_data(data) is True


class TestSaveData:
    """Test save_data method"""

    def get_concrete_scraper(self):
        """Helper to create a concrete scraper"""
        from datagod.scrapers.base_scraper import BaseScraper

        class ConcreteScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        return ConcreteScraper("https://example.com")

    def test_save_data_success(self):
        """Test saving data successfully"""
        scraper = self.get_concrete_scraper()
        data = [{"id": 1}, {"id": 2}]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filename = f.name

        try:
            result = scraper.save_data(data, filename)
            assert result is True

            with open(filename, "r") as f:
                saved_data = json.load(f)
            assert saved_data == data
        finally:
            os.unlink(filename)

    def test_save_data_failure(self):
        """Test saving data to invalid path"""
        scraper = self.get_concrete_scraper()
        data = [{"id": 1}]

        result = scraper.save_data(data, "/nonexistent/path/file.json")
        assert result is False


class TestLogger:
    """Test logging configuration"""

    def test_logger_exists(self):
        """Test that logger is configured"""
        from datagod.scrapers import base_scraper

        assert hasattr(base_scraper, "logger")


class TestModuleExports:
    """Test module exports and structure"""

    def test_module_has_base_scraper(self):
        """Test module exports BaseScraper"""
        from abc import abstractmethod

        from datagod.scrapers.base_scraper import BaseScraper

        # Check scrape is abstract
        assert hasattr(BaseScraper, "scrape")

    def test_abstractmethod_decorator(self):
        """Test scrape method is abstract"""
        from datagod.scrapers.base_scraper import BaseScraper

        # Cannot instantiate directly
        with pytest.raises(TypeError):
            BaseScraper("https://example.com")
