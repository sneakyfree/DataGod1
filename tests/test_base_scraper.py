"""
Tests for BaseScraper class
"""

import pytest
from unittest.mock import patch, MagicMock
import json


class TestBaseScraperInitialization:
    """Tests for BaseScraper initialization"""

    def test_scraper_initialization(self):
        """Test scraper initializes correctly"""
        from datagod.scrapers.base_scraper import BaseScraper

        # Create a concrete implementation for testing
        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper(
            base_url="https://example.com",
            delay=0.5,
            timeout=60
        )

        assert scraper.base_url == "https://example.com"
        assert scraper.delay == 0.5
        assert scraper.timeout == 60

    def test_scraper_strips_trailing_slash(self):
        """Test scraper strips trailing slash from base URL"""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper(base_url="https://example.com/")

        assert scraper.base_url == "https://example.com"

    def test_scraper_default_values(self):
        """Test scraper has correct default values"""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper(base_url="https://example.com")

        assert scraper.delay == 1.0
        assert scraper.timeout == 30

    def test_scraper_session_headers(self):
        """Test scraper session has correct headers"""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper(base_url="https://example.com")

        assert "User-Agent" in scraper.session.headers
        assert "DataGod-Scraper" in scraper.session.headers["User-Agent"]


class TestMakeRequest:
    """Tests for _make_request method"""

    def test_make_get_request_success(self):
        """Test successful GET request"""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper(base_url="https://example.com", delay=0)

        with patch.object(scraper.session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": "test"}
            mock_get.return_value = mock_response

            result = scraper._make_request("https://example.com/api")

            assert result["success"] is True
            assert result["status_code"] == 200
            assert result["data"] == {"data": "test"}

    def test_make_post_request_success(self):
        """Test successful POST request"""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper(base_url="https://example.com", delay=0)

        with patch.object(scraper.session, 'post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"created": True}
            mock_post.return_value = mock_response

            result = scraper._make_request("https://example.com/api", method="POST")

            assert result["success"] is True
            assert result["status_code"] == 201

    def test_make_request_returns_text_on_json_error(self):
        """Test request returns text when JSON parsing fails"""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper(base_url="https://example.com", delay=0)

        with patch.object(scraper.session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_response.text = "<html>Content</html>"
            mock_get.return_value = mock_response

            result = scraper._make_request("https://example.com/page")

            assert result["success"] is True
            assert result["data"] == "<html>Content</html>"

    def test_make_request_unsupported_method(self):
        """Test request raises error for unsupported method"""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper(base_url="https://example.com", delay=0)

        with pytest.raises(ValueError, match="Unsupported HTTP method"):
            scraper._make_request("https://example.com/api", method="DELETE")

    def test_make_request_handles_request_exception(self):
        """Test request handles exceptions gracefully"""
        from datagod.scrapers.base_scraper import BaseScraper
        import requests

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper(base_url="https://example.com", delay=0)

        with patch.object(scraper.session, 'get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

            result = scraper._make_request("https://example.com/api")

            assert result["success"] is False
            assert "Connection failed" in result["error"]


class TestParseJsonData:
    """Tests for _parse_json_data method"""

    def test_parse_json_string(self):
        """Test parsing JSON string"""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper(base_url="https://example.com")

        data = '{"key": "value", "number": 42}'
        result = scraper._parse_json_data(data)

        assert result == {"key": "value", "number": 42}

    def test_parse_json_dict(self):
        """Test passing dict returns dict unchanged"""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper(base_url="https://example.com")

        data = {"already": "parsed"}
        result = scraper._parse_json_data(data)

        assert result == {"already": "parsed"}

    def test_parse_invalid_json_returns_empty_dict(self):
        """Test parsing invalid JSON returns empty dict"""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper(base_url="https://example.com")

        result = scraper._parse_json_data("not valid json")

        assert result == {}


class TestValidateData:
    """Tests for validate_data method"""

    def test_validate_empty_data(self):
        """Test validation fails for empty data"""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper(base_url="https://example.com")

        assert scraper.validate_data({}) is False
        assert scraper.validate_data(None) is False

    def test_validate_missing_required_fields(self):
        """Test validation fails for missing required fields"""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper(base_url="https://example.com")

        data = {"source": "test"}  # Missing scraped_at and data
        assert scraper.validate_data(data) is False

    def test_validate_complete_data(self):
        """Test validation passes for complete data"""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper(base_url="https://example.com")

        data = {
            "source": "test_source",
            "scraped_at": "2024-01-01T00:00:00",
            "data": {"record": "value"}
        }
        assert scraper.validate_data(data) is True


class TestSaveData:
    """Tests for save_data method"""

    def test_save_data_success(self, tmp_path):
        """Test saving data to file"""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper(base_url="https://example.com")

        data = [{"record": "value1"}, {"record": "value2"}]
        filepath = tmp_path / "test_output.json"

        result = scraper.save_data(data, str(filepath))

        assert result is True
        assert filepath.exists()

        # Verify content
        with open(filepath) as f:
            saved_data = json.load(f)
        assert saved_data == data

    def test_save_data_failure(self):
        """Test save_data handles errors"""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper(base_url="https://example.com")

        data = [{"record": "value"}]
        # Invalid path
        result = scraper.save_data(data, "/nonexistent/directory/file.json")

        assert result is False


class TestExtractLinks:
    """Tests for _extract_links method"""

    def test_extract_absolute_links(self):
        """Test extracting absolute links"""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper(base_url="https://example.com")

        html = '''
        <html>
            <a href="https://other.com/page">External</a>
            <a href="http://another.com/path">Another</a>
        </html>
        '''

        links = scraper._extract_links(html, "https://example.com")

        assert "https://other.com/page" in links
        assert "http://another.com/path" in links

    def test_extract_relative_links(self):
        """Test extracting relative links"""
        from datagod.scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            def scrape(self, **kwargs):
                return []

        scraper = TestScraper(base_url="https://example.com")

        html = '''
        <html>
            <a href="/page1">Page 1</a>
            <a href="page2">Page 2</a>
        </html>
        '''

        links = scraper._extract_links(html, "https://example.com")

        assert "https://example.com/page1" in links
        assert "https://example.com/page2" in links


class TestAbstractMethod:
    """Tests for abstract scrape method"""

    def test_cannot_instantiate_base_scraper(self):
        """Test BaseScraper cannot be instantiated directly"""
        from datagod.scrapers.base_scraper import BaseScraper

        with pytest.raises(TypeError):
            BaseScraper(base_url="https://example.com")

    def test_concrete_implementation_works(self):
        """Test concrete implementation can be instantiated"""
        from datagod.scrapers.base_scraper import BaseScraper

        class ConcreteScraper(BaseScraper):
            def scrape(self, **kwargs):
                return [{"data": "test"}]

        scraper = ConcreteScraper(base_url="https://example.com")
        result = scraper.scrape()

        assert result == [{"data": "test"}]
