"""
Tests for datagod/scrapers/property_scraper.py
Tests that actually import and exercise the module for real coverage.
"""
import pytest
from unittest.mock import patch, MagicMock
import logging


class TestPropertyScraperImport:
    """Test PropertyScraper import and basic creation"""

    def test_property_scraper_import(self):
        """Test that PropertyScraper can be imported"""
        from datagod.scrapers.property_scraper import PropertyScraper
        assert PropertyScraper is not None

    def test_property_scraper_inherits_base_scraper(self):
        """Test PropertyScraper inherits from BaseScraper"""
        from datagod.scrapers.property_scraper import PropertyScraper
        from datagod.scrapers.base_scraper import BaseScraper
        assert issubclass(PropertyScraper, BaseScraper)


class TestPropertyScraperInit:
    """Test PropertyScraper initialization"""

    def test_init_default_values(self):
        """Test initialization with default values"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com")
        assert scraper.base_url == "https://example.com"
        assert scraper.delay == 1.0
        assert scraper.timeout == 30
        assert scraper.scraped_count == 0

    def test_init_custom_values(self):
        """Test initialization with custom values"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com", delay=2.0, timeout=60)
        assert scraper.delay == 2.0
        assert scraper.timeout == 60

    def test_init_trailing_slash_removed(self):
        """Test trailing slash removed from base_url"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com/")
        assert scraper.base_url == "https://example.com"


class TestPropertyScraperScrape:
    """Test scrape method"""

    def test_scrape_returns_list(self):
        """Test scrape returns a list"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com")
        result = scraper.scrape()
        assert isinstance(result, list)

    def test_scrape_returns_sample_property(self):
        """Test scrape returns sample property data"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com")
        result = scraper.scrape()

        assert len(result) == 1
        prop = result[0]

        assert "property_id" in prop
        assert "address" in prop
        assert "owner" in prop
        assert "tax_info" in prop
        assert "source" in prop
        assert "scraped_at" in prop

    def test_scrape_increments_count(self):
        """Test scrape increments scraped_count"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com")
        assert scraper.scraped_count == 0

        scraper.scrape()
        assert scraper.scraped_count == 1

        scraper.scrape()
        assert scraper.scraped_count == 2

    def test_scrape_source_matches_base_url(self):
        """Test scraped data source matches base_url"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://county.gov/property")
        result = scraper.scrape()
        assert result[0]["source"] == "https://county.gov/property"

    def test_scrape_address_structure(self):
        """Test scraped address has correct structure"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com")
        result = scraper.scrape()
        address = result[0]["address"]

        assert "street" in address
        assert "city" in address
        assert "state" in address
        assert "zip" in address

    def test_scrape_owner_structure(self):
        """Test scraped owner has correct structure"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com")
        result = scraper.scrape()
        owner = result[0]["owner"]

        assert "name" in owner
        assert "phone" in owner
        assert "email" in owner

    def test_scrape_tax_info_structure(self):
        """Test scraped tax_info has correct structure"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com")
        result = scraper.scrape()
        tax_info = result[0]["tax_info"]

        assert "year" in tax_info
        assert "amount" in tax_info
        assert "status" in tax_info


class TestPropertyScraperScrapeDetails:
    """Test scrape_property_details method"""

    def test_scrape_property_details_returns_dict(self):
        """Test scrape_property_details returns a dict"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com")
        result = scraper.scrape_property_details("PROP-12345")
        assert isinstance(result, dict)

    def test_scrape_property_details_has_property_id(self):
        """Test returned dict has the property_id"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com")
        result = scraper.scrape_property_details("MY-PROPERTY-ID")
        assert result["property_id"] == "MY-PROPERTY-ID"

    def test_scrape_property_details_additional_info(self):
        """Test returned dict has additional_info"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com")
        result = scraper.scrape_property_details("PROP-123")

        assert "additional_info" in result
        info = result["additional_info"]
        assert "assessor_id" in info
        assert "land_value" in info
        assert "building_value" in info
        assert "total_value" in info
        assert "assessment_date" in info

    def test_scrape_property_details_source(self):
        """Test source is included in details"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://county.gov/details")
        result = scraper.scrape_property_details("PROP-123")
        assert result["source"] == "https://county.gov/details"

    def test_scrape_property_details_scraped_at(self):
        """Test scraped_at timestamp is included"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com")
        result = scraper.scrape_property_details("PROP-123")
        assert "scraped_at" in result
        assert len(result["scraped_at"]) > 0  # ISO format timestamp


class TestPropertyScraperScrapeMultiple:
    """Test scrape_multiple_properties method"""

    def test_scrape_multiple_empty_list(self):
        """Test scrape_multiple with empty list"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com")
        result = scraper.scrape_multiple_properties([])
        assert result == []

    def test_scrape_multiple_single_property(self):
        """Test scrape_multiple with single property"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com")
        result = scraper.scrape_multiple_properties(["PROP-1"])
        assert len(result) == 1
        assert result[0]["property_id"] == "PROP-1"

    def test_scrape_multiple_several_properties(self):
        """Test scrape_multiple with several properties"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com")
        result = scraper.scrape_multiple_properties(["PROP-1", "PROP-2", "PROP-3"])

        assert len(result) == 3
        ids = [r["property_id"] for r in result]
        assert "PROP-1" in ids
        assert "PROP-2" in ids
        assert "PROP-3" in ids

    def test_scrape_multiple_returns_list(self):
        """Test scrape_multiple returns a list"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com")
        result = scraper.scrape_multiple_properties(["PROP-1"])
        assert isinstance(result, list)


class TestGetCurrentTimestamp:
    """Test _get_current_timestamp method"""

    def test_get_current_timestamp_format(self):
        """Test timestamp is in ISO format"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com")
        timestamp = scraper._get_current_timestamp()

        # ISO format contains 'T' separator
        assert "T" in timestamp

        # Should be parseable as a date
        from datetime import datetime
        parsed = datetime.fromisoformat(timestamp)
        assert parsed is not None

    def test_get_current_timestamp_recent(self):
        """Test timestamp is recent (within last minute)"""
        from datagod.scrapers.property_scraper import PropertyScraper
        from datetime import datetime, timedelta

        scraper = PropertyScraper("https://example.com")
        timestamp = scraper._get_current_timestamp()
        parsed = datetime.fromisoformat(timestamp)

        now = datetime.utcnow()
        diff = abs((now - parsed).total_seconds())
        assert diff < 60  # Within 1 minute


class TestLogging:
    """Test logging in PropertyScraper"""

    def test_logger_exists(self):
        """Test logger is configured"""
        from datagod.scrapers import property_scraper
        assert hasattr(property_scraper, 'logger')

    def test_scrape_logs_info(self):
        """Test scrape method logs info"""
        from datagod.scrapers.property_scraper import PropertyScraper

        with patch('datagod.scrapers.property_scraper.logger') as mock_logger:
            scraper = PropertyScraper("https://example.com")
            scraper.scrape()
            # Should log start message and completion message
            assert mock_logger.info.called

    def test_scrape_details_logs_info(self):
        """Test scrape_property_details logs info"""
        from datagod.scrapers.property_scraper import PropertyScraper

        with patch('datagod.scrapers.property_scraper.logger') as mock_logger:
            scraper = PropertyScraper("https://example.com")
            scraper.scrape_property_details("PROP-123")
            assert mock_logger.info.called

    def test_scrape_multiple_logs_info(self):
        """Test scrape_multiple_properties logs info"""
        from datagod.scrapers.property_scraper import PropertyScraper

        with patch('datagod.scrapers.property_scraper.logger') as mock_logger:
            scraper = PropertyScraper("https://example.com")
            scraper.scrape_multiple_properties(["PROP-1", "PROP-2"])
            assert mock_logger.info.called


class TestExceptionHandling:
    """Test exception handling in PropertyScraper"""

    def test_scrape_returns_empty_on_exception(self):
        """Test scrape returns empty list on exception"""
        from datagod.scrapers.property_scraper import PropertyScraper

        scraper = PropertyScraper("https://example.com")

        # Simulate exception by patching _get_current_timestamp
        with patch.object(scraper, '_get_current_timestamp', side_effect=Exception("Test error")):
            result = scraper.scrape()
            assert result == []

    def test_scrape_details_returns_empty_on_exception(self):
        """Test scrape_property_details returns empty dict on exception"""
        from datagod.scrapers.property_scraper import PropertyScraper

        scraper = PropertyScraper("https://example.com")

        # Simulate exception
        with patch.object(scraper, '_get_current_timestamp', side_effect=Exception("Test error")):
            result = scraper.scrape_property_details("PROP-123")
            assert result == {}


class TestInheritedMethods:
    """Test methods inherited from BaseScraper"""

    def test_has_make_request(self):
        """Test PropertyScraper has _make_request method"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com")
        assert hasattr(scraper, '_make_request')

    def test_has_session(self):
        """Test PropertyScraper has session"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com")
        assert hasattr(scraper, 'session')

    def test_has_extract_links(self):
        """Test PropertyScraper has _extract_links"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com")
        assert hasattr(scraper, '_extract_links')

    def test_has_save_data(self):
        """Test PropertyScraper has save_data"""
        from datagod.scrapers.property_scraper import PropertyScraper
        scraper = PropertyScraper("https://example.com")
        assert hasattr(scraper, 'save_data')
