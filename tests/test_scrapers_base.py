"""
Tests for base scraper classes.
"""

import pytest
from unittest.mock import MagicMock, patch
import json
import tempfile
import os


class ConcreteScraper:
    """Concrete implementation of BaseScraper for testing."""

    def __init__(self, base_url="https://example.com", delay=0.0, timeout=5):
        from datagod.scrapers.base_scraper import BaseScraper
        self.base_url = base_url.rstrip('/')
        self.delay = delay
        self.timeout = timeout
        self.session = MagicMock()

    def scrape(self, **kwargs):
        return [{"test": "data"}]

    def _make_request(self, url, method='GET', **kwargs):
        from datagod.scrapers.base_scraper import BaseScraper
        # Create a temporary concrete class
        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper(self.base_url, self.delay, self.timeout)
        return scraper._make_request(url, method, **kwargs)

    def _extract_links(self, html_content, base_url):
        from datagod.scrapers.base_scraper import BaseScraper
        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []
        scraper = TestScraper(self.base_url)
        return scraper._extract_links(html_content, base_url)

    def _parse_json_data(self, data):
        from datagod.scrapers.base_scraper import BaseScraper
        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []
        scraper = TestScraper(self.base_url)
        return scraper._parse_json_data(data)

    def validate_data(self, data):
        from datagod.scrapers.base_scraper import BaseScraper
        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []
        scraper = TestScraper(self.base_url)
        return scraper.validate_data(data)

    def save_data(self, data, filename):
        from datagod.scrapers.base_scraper import BaseScraper
        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []
        scraper = TestScraper(self.base_url)
        return scraper.save_data(data, filename)


class TestBaseScraper:
    """Tests for BaseScraper class."""

    def test_base_scraper_import(self):
        """Test BaseScraper can be imported."""
        from datagod.scrapers.base_scraper import BaseScraper
        assert BaseScraper is not None

    def test_base_scraper_is_abstract(self):
        """Test BaseScraper is abstract and cannot be instantiated directly."""
        from datagod.scrapers.base_scraper import BaseScraper
        from abc import ABC
        assert issubclass(BaseScraper, ABC)

    def test_concrete_scraper_creation(self):
        """Test concrete implementation can be created."""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return [{"test": "data"}]

        scraper = TestScraper("https://example.com")
        assert scraper is not None
        assert scraper.base_url == "https://example.com"

    def test_scraper_strips_trailing_slash(self):
        """Test base_url strips trailing slash."""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper("https://example.com/")
        assert scraper.base_url == "https://example.com"

    def test_scraper_default_values(self):
        """Test default delay and timeout values."""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper("https://example.com")
        assert scraper.delay == 1.0
        assert scraper.timeout == 30

    def test_scraper_custom_values(self):
        """Test custom delay and timeout values."""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper("https://example.com", delay=0.5, timeout=60)
        assert scraper.delay == 0.5
        assert scraper.timeout == 60

    def test_scraper_has_session(self):
        """Test scraper has requests session."""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper("https://example.com")
        assert scraper.session is not None

    def test_scraper_session_headers(self):
        """Test session has proper headers."""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper("https://example.com")
        assert 'User-Agent' in scraper.session.headers


class TestBaseScraperMethods:
    """Tests for BaseScraper methods."""

    def test_parse_json_data_with_dict(self):
        """Test parsing already-parsed JSON data."""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper("https://example.com")
        data = {"key": "value"}
        result = scraper._parse_json_data(data)
        assert result == data

    def test_parse_json_data_with_string(self):
        """Test parsing JSON string."""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper("https://example.com")
        data = '{"key": "value"}'
        result = scraper._parse_json_data(data)
        assert result == {"key": "value"}

    def test_parse_json_data_with_invalid_string(self):
        """Test parsing invalid JSON string."""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper("https://example.com")
        data = "not valid json"
        result = scraper._parse_json_data(data)
        assert result == {}

    def test_validate_data_empty(self):
        """Test validating empty data."""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper("https://example.com")
        assert scraper.validate_data({}) is False
        assert scraper.validate_data(None) is False

    def test_validate_data_missing_fields(self):
        """Test validating data with missing required fields."""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper("https://example.com")
        data = {"source": "test"}  # Missing 'scraped_at' and 'data'
        assert scraper.validate_data(data) is False

    def test_validate_data_valid(self):
        """Test validating valid data."""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper("https://example.com")
        data = {
            "source": "test",
            "scraped_at": "2023-01-01",
            "data": {"key": "value"}
        }
        assert scraper.validate_data(data) is True

    def test_save_data(self):
        """Test saving data to file."""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper("https://example.com")
        data = [{"key": "value"}]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filename = f.name

        try:
            result = scraper.save_data(data, filename)
            assert result is True

            # Verify file contents
            with open(filename, 'r') as f:
                saved_data = json.load(f)
            assert saved_data == data
        finally:
            os.unlink(filename)

    def test_save_data_invalid_path(self):
        """Test saving data to invalid path."""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper("https://example.com")
        data = [{"key": "value"}]

        result = scraper.save_data(data, "/invalid/path/that/does/not/exist/data.json")
        assert result is False


class TestBaseScraperExtractLinks:
    """Tests for link extraction."""

    def test_extract_links_simple(self):
        """Test extracting links from simple HTML."""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper("https://example.com")
        html = '''
        <html>
            <a href="/page1">Page 1</a>
            <a href="/page2">Page 2</a>
        </html>
        '''

        links = scraper._extract_links(html, "https://example.com")
        assert len(links) == 2
        assert "https://example.com/page1" in links
        assert "https://example.com/page2" in links

    def test_extract_links_absolute(self):
        """Test extracting absolute links."""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper("https://example.com")
        html = '''
        <html>
            <a href="https://other.com/page">Other Page</a>
        </html>
        '''

        links = scraper._extract_links(html, "https://example.com")
        assert len(links) == 1
        assert "https://other.com/page" in links

    def test_extract_links_relative(self):
        """Test extracting relative links."""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper("https://example.com")
        html = '''
        <html>
            <a href="page.html">Page</a>
        </html>
        '''

        links = scraper._extract_links(html, "https://example.com")
        assert len(links) == 1
        assert "https://example.com/page.html" in links


class TestBaseScraperMakeRequest:
    """Tests for making HTTP requests."""

    @patch('datagod.scrapers.base_scraper.time.sleep')
    def test_make_request_get(self, mock_sleep):
        """Test making GET request."""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper("https://example.com", delay=0.0)

        with patch.object(scraper.session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": "test"}
            mock_get.return_value = mock_response

            result = scraper._make_request("https://example.com/api")
            assert result['success'] is True
            assert result['status_code'] == 200

    @patch('datagod.scrapers.base_scraper.time.sleep')
    def test_make_request_post(self, mock_sleep):
        """Test making POST request."""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper("https://example.com", delay=0.0)

        with patch.object(scraper.session, 'post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"created": True}
            mock_post.return_value = mock_response

            result = scraper._make_request("https://example.com/api", method='POST')
            assert result['success'] is True
            assert result['status_code'] == 201

    @patch('datagod.scrapers.base_scraper.time.sleep')
    def test_make_request_unsupported_method(self, mock_sleep):
        """Test making request with unsupported method."""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper("https://example.com", delay=0.0)

        with pytest.raises(ValueError) as excinfo:
            scraper._make_request("https://example.com/api", method='DELETE')
        assert "Unsupported HTTP method" in str(excinfo.value)

    @patch('datagod.scrapers.base_scraper.time.sleep')
    def test_make_request_json_parse_error(self, mock_sleep):
        """Test making request when JSON parsing fails."""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper("https://example.com", delay=0.0)

        with patch.object(scraper.session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_response.text = "Plain text response"
            mock_get.return_value = mock_response

            result = scraper._make_request("https://example.com/api")
            assert result['success'] is True
            assert result['data'] == "Plain text response"
