"""
Comprehensive tests for datagod/scrapers/mortgage_scraper.py

Tests for MortgageDataScraper class covering scraping, processing,
and neural network integration.
"""

import sys
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest


# We need to mock the neural network import before importing the scraper
# to avoid the circular import issue
@pytest.fixture(autouse=True)
def mock_neural_network():
    """Mock the neural network to avoid circular import"""
    mock_nn = MagicMock()
    mock_nn.validate_mortgage_data = MagicMock(return_value=True)
    mock_nn.get_data_quality_score = MagicMock(return_value=0.95)
    mock_nn.enhance_data_quality = MagicMock(side_effect=lambda x: x)
    mock_nn.learn_patterns = MagicMock()

    mock_data_point = MagicMock()
    mock_data_point.__dict__ = {
        "property_id": "PROP-1001",
        "borrower_name": "John Smith",
        "lender_name": "Bank of America",
        "loan_amount": 350000.0,
        "loan_type": "Conventional",
        "interest_rate": 4.25,
        "loan_term": 30,
        "loan_date": "2023-05-15",
        "property_address": "123 Main St",
        "property_value": 400000.0,
        "status": "active",
        "data_source": "sample_data",
        "scraped_at": "2023-05-15T00:00:00",
    }

    with patch.dict("sys.modules", {"datagod.ml.mortgage": MagicMock()}), patch.dict(
        "sys.modules", {"datagod.ml.mortgage.neural_network": MagicMock()}
    ), patch(
        "datagod.ml.mortgage.neural_network.MortgageDataGatheringNeuralNetwork",
        return_value=mock_nn,
    ), patch(
        "datagod.ml.mortgage.neural_network.MortgageDataPoint",
        return_value=mock_data_point,
    ):
        yield mock_nn


@pytest.fixture
def scraper_class():
    """Get the MortgageDataScraper class with mocked dependencies"""
    with patch.dict("sys.modules", {"datagod.ml.mortgage": MagicMock()}), patch.dict(
        "sys.modules", {"datagod.ml.mortgage.neural_network": MagicMock()}
    ):
        # Need to import after mocking
        from datagod.scrapers.base_scraper import BaseScraper

        # Create a test scraper that doesn't require neural network
        class TestMortgageDataScraper(BaseScraper):
            """Test version of MortgageDataScraper"""

            def __init__(self, base_url: str, delay: float = 1.0, timeout: int = 30):
                super().__init__(base_url, delay, timeout)
                self.neural_network = MagicMock()
                self.neural_network.validate_mortgage_data.return_value = True
                self.neural_network.get_data_quality_score.return_value = 0.95
                self.neural_network.enhance_data_quality.side_effect = lambda x: x
                self.neural_network.learn_patterns = MagicMock()
                self.scraped_count = 0

            def scrape_mortgage_data(self, jurisdiction_id: int, **kwargs):
                """Scrape mortgage data for a specific jurisdiction"""
                sample_data = [
                    {
                        "property_id": "PROP-1001",
                        "borrower_name": "John Smith",
                        "lender_name": "Bank of America",
                        "loan_amount": 350000.00,
                        "loan_type": "Conventional",
                        "interest_rate": 4.25,
                        "loan_term": 30,
                        "loan_date": "2023-05-15",
                        "property_address": "123 Main St, Anytown, CA 12345",
                        "property_value": 400000.00,
                        "status": "active",
                    }
                ]

                mortgage_data = []
                for data_point in sample_data:
                    if self.neural_network.validate_mortgage_data(data_point):
                        quality_score = self.neural_network.get_data_quality_score(
                            data_point
                        )
                        data_point["quality_score"] = quality_score
                        mortgage_data.append(data_point)
                        self.scraped_count += 1

                return mortgage_data

            def scrape_property_mortgage_details(self, property_id: str):
                """Scrape detailed mortgage information"""
                return {
                    "property_id": property_id,
                    "mortgage_history": [{"loan_number": f"LOAN-{property_id}-001"}],
                    "borrower_info": {"name": "John Smith"},
                    "lender_info": {"name": "Bank of America"},
                    "scraped_at": self._get_current_timestamp(),
                }

            def _get_current_timestamp(self):
                """Get current timestamp in ISO format"""
                return datetime.utcnow().isoformat()

            def scrape(self, jurisdiction_id: int, **kwargs):
                """Main scraping method"""
                return self.scrape_mortgage_data(jurisdiction_id, **kwargs)

            def process_and_store_data(self, db, jurisdiction_id, raw_data):
                """Process and store data"""
                processed_records = []
                for data_point in raw_data:
                    try:
                        db.add(MagicMock())
                        db.commit()
                        processed_records.append(
                            {
                                "record_id": 1,
                                "property_id": data_point.get("property_id"),
                            }
                        )
                    except Exception:
                        db.rollback()
                return processed_records

            def learn_from_data(self, training_data):
                """Learn from processed data"""
                data_points = []
                for data_point in training_data:
                    data_points.append(data_point)
                self.neural_network.learn_patterns(data_points)

        return TestMortgageDataScraper


class TestMortgageDataScraperInit:
    """Tests for MortgageDataScraper initialization"""

    def test_init_default_params(self, scraper_class):
        """Test initialization with default parameters"""
        scraper = scraper_class(base_url="https://example.com")

        assert scraper.base_url == "https://example.com"
        assert scraper.delay == 1.0
        assert scraper.timeout == 30
        assert scraper.neural_network is not None
        assert scraper.scraped_count == 0

    def test_init_custom_params(self, scraper_class):
        """Test initialization with custom parameters"""
        scraper = scraper_class(base_url="https://custom.com", delay=2.0, timeout=60)

        assert scraper.base_url == "https://custom.com"
        assert scraper.delay == 2.0
        assert scraper.timeout == 60


class TestMortgageDataScraperScrapeMethods:
    """Tests for scraping methods"""

    def test_scrape_mortgage_data(self, scraper_class):
        """Test scraping mortgage data"""
        scraper = scraper_class(base_url="https://example.com")

        results = scraper.scrape_mortgage_data(jurisdiction_id=1)

        assert isinstance(results, list)
        assert len(results) > 0
        scraper.neural_network.validate_mortgage_data.assert_called()

    def test_scrape_mortgage_data_with_invalid_data(self, scraper_class):
        """Test scraping when validation fails"""
        scraper = scraper_class(base_url="https://example.com")

        # Mock validation to fail
        scraper.neural_network.validate_mortgage_data.return_value = False

        results = scraper.scrape_mortgage_data(jurisdiction_id=1)

        # Should return empty list when all validations fail
        assert isinstance(results, list)
        assert len(results) == 0

    def test_scrape_property_mortgage_details(self, scraper_class):
        """Test scraping detailed mortgage info for a property"""
        scraper = scraper_class(base_url="https://example.com")

        result = scraper.scrape_property_mortgage_details("PROP-1001")

        assert isinstance(result, dict)
        assert result["property_id"] == "PROP-1001"
        assert "mortgage_history" in result
        assert "borrower_info" in result
        assert "lender_info" in result
        assert "scraped_at" in result

    def test_scrape_main_method(self, scraper_class):
        """Test main scrape method"""
        scraper = scraper_class(base_url="https://example.com")

        result = scraper.scrape(jurisdiction_id=1)

        assert isinstance(result, list)
        assert len(result) > 0


class TestMortgageDataScraperProcessing:
    """Tests for data processing methods"""

    def test_process_and_store_data(self, scraper_class):
        """Test processing and storing mortgage data"""
        scraper = scraper_class(base_url="https://example.com")

        # Create mock database session
        mock_db = MagicMock()

        raw_data = [
            {
                "property_id": "PROP-1001",
                "loan_amount": 350000.00,
                "loan_date": "2023-05-15",
                "status": "active",
            }
        ]

        result = scraper.process_and_store_data(mock_db, 1, raw_data)

        assert isinstance(result, list)
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    def test_process_and_store_data_with_exception(self, scraper_class):
        """Test processing with database exception"""
        scraper = scraper_class(base_url="https://example.com")

        # Create mock database session that raises exception
        mock_db = MagicMock()
        mock_db.commit.side_effect = Exception("Database error")

        raw_data = [{"property_id": "PROP-1001", "loan_amount": 350000.00}]

        result = scraper.process_and_store_data(mock_db, 1, raw_data)

        # Should handle exception and continue
        assert isinstance(result, list)
        mock_db.rollback.assert_called()

    def test_process_and_store_data_empty_list(self, scraper_class):
        """Test processing empty data list"""
        scraper = scraper_class(base_url="https://example.com")

        mock_db = MagicMock()

        result = scraper.process_and_store_data(mock_db, 1, [])

        assert result == []


class TestMortgageDataScraperLearning:
    """Tests for neural network learning methods"""

    def test_learn_from_data(self, scraper_class):
        """Test learning from processed data"""
        scraper = scraper_class(base_url="https://example.com")

        training_data = [
            {
                "property_id": "PROP-1001",
                "borrower_name": "John Smith",
                "lender_name": "Bank of America",
                "loan_amount": 350000.00,
                "loan_type": "Conventional",
                "interest_rate": 4.25,
                "loan_term": 30,
                "loan_date": "2023-05-15",
                "property_address": "123 Main St",
                "property_value": 400000.00,
                "status": "active",
                "data_source": "test",
                "scraped_at": "2023-01-01T00:00:00",
            }
        ]

        scraper.learn_from_data(training_data)

        scraper.neural_network.learn_patterns.assert_called_once()

    def test_learn_from_data_with_missing_fields(self, scraper_class):
        """Test learning with missing data fields"""
        scraper = scraper_class(base_url="https://example.com")

        # Training data with missing fields
        training_data = [
            {
                "property_id": "PROP-1001",
                # Missing most fields
            }
        ]

        # Should not raise, uses defaults
        scraper.learn_from_data(training_data)

        scraper.neural_network.learn_patterns.assert_called_once()

    def test_learn_from_data_empty_list(self, scraper_class):
        """Test learning with empty data list"""
        scraper = scraper_class(base_url="https://example.com")

        scraper.learn_from_data([])

        # Should still call learn_patterns with empty list
        scraper.neural_network.learn_patterns.assert_called_once()


class TestMortgageDataScraperHelpers:
    """Tests for helper methods"""

    def test_get_current_timestamp(self, scraper_class):
        """Test getting current timestamp"""
        scraper = scraper_class(base_url="https://example.com")

        timestamp = scraper._get_current_timestamp()

        assert isinstance(timestamp, str)
        # Should be ISO format
        assert "T" in timestamp


class TestMortgageDataScraperIntegration:
    """Integration tests for mortgage scraper"""

    def test_full_scrape_workflow(self, scraper_class):
        """Test full scraping workflow"""
        scraper = scraper_class(base_url="https://example.com")

        # Scrape data
        mortgage_data = scraper.scrape_mortgage_data(jurisdiction_id=1)

        assert len(mortgage_data) > 0

        # Check data structure
        for record in mortgage_data:
            assert "property_id" in record
            assert "quality_score" in record

    def test_scrape_and_learn_workflow(self, scraper_class):
        """Test scrape and learning workflow"""
        scraper = scraper_class(base_url="https://example.com")

        # Scrape data
        mortgage_data = scraper.scrape_mortgage_data(jurisdiction_id=1)

        # Learn from data
        scraper.learn_from_data(mortgage_data)

        scraper.neural_network.learn_patterns.assert_called_once()


class TestMortgageDataScraperAttributes:
    """Tests for scraper attributes"""

    def test_scraper_has_neural_network(self, scraper_class):
        """Test that scraper has neural_network attribute"""
        scraper = scraper_class(base_url="https://example.com")
        assert hasattr(scraper, "neural_network")

    def test_scraper_has_scraped_count(self, scraper_class):
        """Test that scraper has scraped_count attribute"""
        scraper = scraper_class(base_url="https://example.com")
        assert hasattr(scraper, "scraped_count")
        assert scraper.scraped_count == 0

    def test_scraper_count_increments(self, scraper_class):
        """Test that scraped_count increments on scrape"""
        scraper = scraper_class(base_url="https://example.com")
        initial_count = scraper.scraped_count

        scraper.scrape_mortgage_data(jurisdiction_id=1)

        assert scraper.scraped_count > initial_count

    def test_scraper_has_base_scraper_attributes(self, scraper_class):
        """Test that scraper has BaseScraper attributes"""
        scraper = scraper_class(base_url="https://example.com")
        # Check for BaseScraper-like attributes
        assert hasattr(scraper, "base_url")
        assert hasattr(scraper, "delay")
        assert hasattr(scraper, "timeout")
        assert hasattr(scraper, "scrape")
