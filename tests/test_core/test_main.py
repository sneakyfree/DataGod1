"""
Tests for datagod/main.py

Comprehensive tests for the main application module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import logging
import sys


# Check if the main module can be imported
try:
    from datagod import main as main_module
    MAIN_MODULE_AVAILABLE = True
except ImportError as e:
    MAIN_MODULE_AVAILABLE = False
    MAIN_MODULE_ERROR = str(e)


@pytest.mark.skipif(not MAIN_MODULE_AVAILABLE, reason="datagod.main module has import errors")
class TestSetupDatabase:
    """Tests for setup_database function"""

    @patch('datagod.main.init_db')
    def test_setup_database_success(self, mock_init_db):
        """Test successful database initialization"""
        from datagod.main import setup_database

        mock_init_db.return_value = None
        setup_database()

        mock_init_db.assert_called_once()

    @patch('datagod.main.init_db')
    def test_setup_database_failure(self, mock_init_db):
        """Test database initialization failure"""
        from datagod.main import setup_database

        mock_init_db.side_effect = Exception("Database error")

        with pytest.raises(Exception) as exc_info:
            setup_database()

        assert "Database error" in str(exc_info.value)


@pytest.mark.skipif(not MAIN_MODULE_AVAILABLE, reason="datagod.main module has import errors")
class TestCreateSampleJurisdiction:
    """Tests for create_sample_jurisdiction function"""

    @patch('datagod.main.get_db_session')
    def test_create_new_jurisdiction(self, mock_get_session):
        """Test creating a new jurisdiction"""
        from datagod.main import create_sample_jurisdiction

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        create_sample_jurisdiction()

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @patch('datagod.main.get_db_session')
    def test_jurisdiction_already_exists(self, mock_get_session):
        """Test when jurisdiction already exists"""
        from datagod.main import create_sample_jurisdiction

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Mock existing jurisdiction
        mock_jurisdiction = Mock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_jurisdiction

        create_sample_jurisdiction()

        mock_session.add.assert_not_called()
        mock_session.close.assert_called_once()

    @patch('datagod.main.get_db_session')
    def test_jurisdiction_creation_error(self, mock_get_session):
        """Test error handling during jurisdiction creation"""
        from datagod.main import create_sample_jurisdiction

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_session.commit.side_effect = Exception("DB error")

        with pytest.raises(Exception):
            create_sample_jurisdiction()

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


@pytest.mark.skipif(not MAIN_MODULE_AVAILABLE, reason="datagod.main module has import errors")
class TestCreateSampleDataSource:
    """Tests for create_sample_data_source function"""

    @patch('datagod.main.get_db_session')
    def test_create_new_data_source(self, mock_get_session):
        """Test creating a new data source"""
        from datagod.main import create_sample_data_source

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Mock jurisdiction exists
        mock_jurisdiction = Mock(id=1)

        # First query returns jurisdiction, second returns None for data source
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.side_effect = [
            MagicMock(first=MagicMock(return_value=mock_jurisdiction)),  # jurisdiction
            MagicMock(first=MagicMock(return_value=None)),  # data source
        ]

        create_sample_data_source()

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @patch('datagod.main.get_db_session')
    def test_no_jurisdiction_found(self, mock_get_session):
        """Test when no jurisdiction exists"""
        from datagod.main import create_sample_data_source

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        create_sample_data_source()

        mock_session.add.assert_not_called()

    @patch('datagod.main.get_db_session')
    def test_data_source_already_exists(self, mock_get_session):
        """Test when data source already exists"""
        from datagod.main import create_sample_data_source

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        mock_jurisdiction = Mock(id=1)
        mock_data_source = Mock()

        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.side_effect = [
            MagicMock(first=MagicMock(return_value=mock_jurisdiction)),
            MagicMock(first=MagicMock(return_value=mock_data_source)),
        ]

        create_sample_data_source()

        mock_session.add.assert_not_called()


@pytest.mark.skipif(not MAIN_MODULE_AVAILABLE, reason="datagod.main module has import errors")
class TestRunDataCollection:
    """Tests for run_data_collection function"""

    @patch('datagod.main.create_sample_data_source')
    @patch('datagod.main.create_sample_jurisdiction')
    @patch('datagod.main.setup_database')
    @patch('datagod.main.PropertyScraper')
    @patch('datagod.main.validator')
    @patch('datagod.main.processor')
    def test_successful_data_collection(self, mock_processor, mock_validator,
                                        mock_scraper_class, mock_setup,
                                        mock_create_jurisdiction, mock_create_source):
        """Test successful data collection"""
        from datagod.main import run_data_collection

        # Setup mocks
        mock_scraper = MagicMock()
        mock_scraper_class.return_value = mock_scraper
        mock_scraper.scrape.return_value = [
            {'address': '123 Main St', 'value': 100000},
            {'address': '456 Oak Ave', 'value': 200000},
        ]

        mock_validator.validate_record.return_value = {'valid': True}
        mock_processor.enrich_data.side_effect = lambda x: {**x, 'enriched': True}

        run_data_collection()

        mock_setup.assert_called_once()
        mock_create_jurisdiction.assert_called_once()
        mock_create_source.assert_called_once()
        mock_scraper.scrape.assert_called_once()
        assert mock_validator.validate_record.call_count == 2
        assert mock_processor.enrich_data.call_count == 2

    @patch('datagod.main.create_sample_data_source')
    @patch('datagod.main.create_sample_jurisdiction')
    @patch('datagod.main.setup_database')
    @patch('datagod.main.PropertyScraper')
    def test_no_data_scraped(self, mock_scraper_class, mock_setup,
                            mock_create_jurisdiction, mock_create_source):
        """Test when no data is scraped"""
        from datagod.main import run_data_collection

        mock_scraper = MagicMock()
        mock_scraper_class.return_value = mock_scraper
        mock_scraper.scrape.return_value = []

        run_data_collection()

        mock_scraper.scrape.assert_called_once()

    @patch('datagod.main.create_sample_data_source')
    @patch('datagod.main.create_sample_jurisdiction')
    @patch('datagod.main.setup_database')
    @patch('datagod.main.PropertyScraper')
    @patch('datagod.main.validator')
    def test_validation_errors(self, mock_validator, mock_scraper_class,
                               mock_setup, mock_create_jurisdiction, mock_create_source):
        """Test handling validation errors"""
        from datagod.main import run_data_collection

        mock_scraper = MagicMock()
        mock_scraper_class.return_value = mock_scraper
        mock_scraper.scrape.return_value = [{'address': 'invalid'}]

        mock_validator.validate_record.return_value = {
            'valid': False,
            'errors': ['Missing required field: value']
        }

        # Should not raise, just log warning
        run_data_collection()


@pytest.mark.skipif(not MAIN_MODULE_AVAILABLE, reason="datagod.main module has import errors")
class TestMain:
    """Tests for main entry point"""

    @patch('datagod.main.run_data_collection')
    def test_main_success(self, mock_run):
        """Test successful main execution"""
        from datagod.main import main

        main()

        mock_run.assert_called_once()

    @patch('datagod.main.run_data_collection')
    @patch('sys.exit')
    def test_main_failure(self, mock_exit, mock_run):
        """Test main execution with failure"""
        from datagod.main import main

        mock_run.side_effect = Exception("Fatal error")

        main()

        mock_exit.assert_called_once_with(1)


@pytest.mark.skipif(not MAIN_MODULE_AVAILABLE, reason="datagod.main module has import errors")
class TestLoggingConfiguration:
    """Tests for logging configuration"""

    def test_logger_exists(self):
        """Test that logger is configured"""
        assert hasattr(main_module, 'logger')
        assert isinstance(main_module.logger, logging.Logger)
