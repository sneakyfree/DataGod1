"""
Tests for datagod/scrapers/api_integration.py
Tests that actually import and exercise the module for real coverage.
"""

import json
import os
import tempfile
import time
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestAPIIntegrationConfig:
    """Test APIIntegrationConfig dataclass"""

    def test_config_import(self):
        """Test that APIIntegrationConfig can be imported"""
        from datagod.scrapers.api_integration import APIIntegrationConfig

        assert APIIntegrationConfig is not None

    def test_config_required_fields(self):
        """Test creating config with required fields"""
        from datagod.scrapers.api_integration import APIIntegrationConfig

        config = APIIntegrationConfig(
            name="test_api", base_url="https://api.example.com"
        )

        assert config.name == "test_api"
        assert config.base_url == "https://api.example.com"

    def test_config_default_values(self):
        """Test config default values"""
        from datagod.scrapers.api_integration import APIIntegrationConfig

        config = APIIntegrationConfig(name="test", base_url="https://test.com")

        assert config.api_key is None
        assert config.rate_limit == 10
        assert config.rate_limit_period == 60
        assert config.timeout == 30
        assert config.retry_count == 3
        assert config.retry_delay == 5

    def test_config_custom_values(self):
        """Test config with custom values"""
        from datagod.scrapers.api_integration import APIIntegrationConfig

        config = APIIntegrationConfig(
            name="custom",
            base_url="https://custom.com",
            api_key="secret123",
            rate_limit=20,
            rate_limit_period=120,
            timeout=60,
            retry_count=5,
            retry_delay=10,
        )

        assert config.api_key == "secret123"
        assert config.rate_limit == 20
        assert config.rate_limit_period == 120
        assert config.timeout == 60
        assert config.retry_count == 5
        assert config.retry_delay == 10


class TestBaseAPIIntegration:
    """Test BaseAPIIntegration class"""

    def get_test_config(self, api_key=None):
        """Helper to create test config"""
        from datagod.scrapers.api_integration import APIIntegrationConfig

        return APIIntegrationConfig(
            name="test_api",
            base_url="https://api.example.com",
            api_key=api_key,
            rate_limit=5,
            rate_limit_period=1,  # Short for testing
        )

    def test_base_api_integration_is_abstract(self):
        """Test BaseAPIIntegration is abstract"""
        from abc import ABC

        from datagod.scrapers.api_integration import BaseAPIIntegration

        assert issubclass(BaseAPIIntegration, ABC)

    def test_concrete_integration_creation(self):
        """Test creating a concrete integration"""
        from datagod.scrapers.api_integration import (
            APIIntegrationConfig,
            BaseAPIIntegration,
        )

        class ConcreteIntegration(BaseAPIIntegration):
            def get_records(self, params):
                return []

            def normalize_record(self, record):
                return record

        config = self.get_test_config()
        integration = ConcreteIntegration(config)

        assert integration.config == config
        assert integration.session is not None
        assert integration.last_request_time == 0
        assert integration.request_count == 0

    def test_session_headers_without_api_key(self):
        """Test session headers without API key"""
        from datagod.scrapers.api_integration import (
            APIIntegrationConfig,
            BaseAPIIntegration,
        )

        class ConcreteIntegration(BaseAPIIntegration):
            def get_records(self, params):
                return []

            def normalize_record(self, record):
                return record

        config = self.get_test_config()
        integration = ConcreteIntegration(config)

        assert "User-Agent" in integration.session.headers
        assert "Accept" in integration.session.headers
        assert integration.session.headers["Accept"] == "application/json"
        assert "Authorization" not in integration.session.headers

    def test_session_headers_with_api_key(self):
        """Test session headers with API key"""
        from datagod.scrapers.api_integration import (
            APIIntegrationConfig,
            BaseAPIIntegration,
        )

        class ConcreteIntegration(BaseAPIIntegration):
            def get_records(self, params):
                return []

            def normalize_record(self, record):
                return record

        config = self.get_test_config(api_key="test_key_123")
        integration = ConcreteIntegration(config)

        assert "Authorization" in integration.session.headers
        assert integration.session.headers["Authorization"] == "Bearer test_key_123"

    def test_close(self):
        """Test closing the integration"""
        from datagod.scrapers.api_integration import (
            APIIntegrationConfig,
            BaseAPIIntegration,
        )

        class ConcreteIntegration(BaseAPIIntegration):
            def get_records(self, params):
                return []

            def normalize_record(self, record):
                return record

        config = self.get_test_config()
        integration = ConcreteIntegration(config)
        integration.close()
        # Should not raise an error


class TestRateLimiting:
    """Test rate limiting functionality"""

    def get_concrete_integration(self, rate_limit=5, period=60):
        """Helper to create concrete integration"""
        from datagod.scrapers.api_integration import (
            APIIntegrationConfig,
            BaseAPIIntegration,
        )

        class ConcreteIntegration(BaseAPIIntegration):
            def get_records(self, params):
                return []

            def normalize_record(self, record):
                return record

        config = APIIntegrationConfig(
            name="test",
            base_url="https://test.com",
            rate_limit=rate_limit,
            rate_limit_period=period,
        )
        return ConcreteIntegration(config)

    def test_check_rate_limit_first_request(self):
        """Test first request passes rate limit"""
        integration = self.get_concrete_integration()
        integration._check_rate_limit()
        assert integration.request_count == 1

    def test_check_rate_limit_increments(self):
        """Test request count increments"""
        integration = self.get_concrete_integration()

        for _ in range(3):
            integration._check_rate_limit()

        assert integration.request_count == 3

    def test_rate_limit_window_reset(self):
        """Test rate limit resets after window"""
        integration = self.get_concrete_integration(rate_limit=5, period=0.1)

        for _ in range(5):
            integration._check_rate_limit()
        assert integration.request_count == 5

        # Wait for window to pass
        time.sleep(0.15)

        # Next request should reset
        integration._check_rate_limit()
        assert integration.request_count == 1


class TestMakeRequest:
    """Test _make_request method"""

    def get_concrete_integration(self):
        """Helper to create concrete integration"""
        from datagod.scrapers.api_integration import (
            APIIntegrationConfig,
            BaseAPIIntegration,
        )

        class ConcreteIntegration(BaseAPIIntegration):
            def get_records(self, params):
                return []

            def normalize_record(self, record):
                return record

        config = APIIntegrationConfig(
            name="test",
            base_url="https://api.example.com",
            rate_limit=100,
            rate_limit_period=60,
            retry_count=2,
            retry_delay=0.1,
        )
        return ConcreteIntegration(config)

    def test_make_request_success(self):
        """Test successful request"""
        integration = self.get_concrete_integration()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "value"}

        with patch.object(integration.session, "request", return_value=mock_response):
            result = integration._make_request("GET", "/endpoint")

        assert result == {"data": "value"}

    def test_make_request_error_status(self):
        """Test request with error status"""
        integration = self.get_concrete_integration()

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        with patch.object(integration.session, "request", return_value=mock_response):
            result = integration._make_request("GET", "/notfound")

        assert result is None

    def test_make_request_rate_limited(self):
        """Test handling 429 rate limit"""
        integration = self.get_concrete_integration()

        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "0"}

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"success": True}

        with patch.object(
            integration.session,
            "request",
            side_effect=[mock_response_429, mock_response_200],
        ):
            result = integration._make_request("GET", "/endpoint")

        assert result == {"success": True}

    def test_make_request_exception(self):
        """Test request exception handling"""
        import requests

        integration = self.get_concrete_integration()

        with patch.object(
            integration.session,
            "request",
            side_effect=requests.exceptions.Timeout("Timeout"),
        ):
            result = integration._make_request("GET", "/endpoint")

        assert result is None


class TestAPIIntegrationManager:
    """Test APIIntegrationManager class"""

    def test_manager_init(self):
        """Test manager initialization"""
        from datagod.scrapers.api_integration import APIIntegrationManager

        with patch("os.makedirs"):
            manager = APIIntegrationManager()

        assert manager.integrations == {}
        assert manager.base_dir == "datagod/scrapers/data"

    def test_add_integration(self):
        """Test adding an integration"""
        from datagod.scrapers.api_integration import (
            APIIntegrationConfig,
            APIIntegrationManager,
            MockAPIIntegration,
        )

        with patch("os.makedirs"):
            manager = APIIntegrationManager()

        config = APIIntegrationConfig(name="test", base_url="https://test.com")
        integration = MockAPIIntegration(config)

        manager.add_integration("test_api", integration)

        assert "test_api" in manager.integrations
        assert manager.integrations["test_api"] == integration

    def test_get_integration_exists(self):
        """Test getting existing integration"""
        from datagod.scrapers.api_integration import (
            APIIntegrationConfig,
            APIIntegrationManager,
            MockAPIIntegration,
        )

        with patch("os.makedirs"):
            manager = APIIntegrationManager()

        config = APIIntegrationConfig(name="test", base_url="https://test.com")
        integration = MockAPIIntegration(config)
        manager.add_integration("my_api", integration)

        result = manager.get_integration("my_api")
        assert result == integration

    def test_get_integration_not_exists(self):
        """Test getting non-existent integration"""
        from datagod.scrapers.api_integration import APIIntegrationManager

        with patch("os.makedirs"):
            manager = APIIntegrationManager()

        result = manager.get_integration("nonexistent")
        assert result is None


class TestCollectData:
    """Test collect_data method"""

    def test_collect_data_success(self):
        """Test successful data collection"""
        from datagod.scrapers.api_integration import (
            APIIntegrationConfig,
            APIIntegrationManager,
            MockAPIIntegration,
        )

        with patch("os.makedirs"):
            manager = APIIntegrationManager()

        config = APIIntegrationConfig(name="mock", base_url="https://mock.com")
        integration = MockAPIIntegration(config)
        manager.add_integration("mock", integration)

        data = manager.collect_data("mock", {})

        assert len(data) == 10
        assert all("source" in d for d in data)
        assert all(d["source"] == "mock_api" for d in data)

    def test_collect_data_not_found(self):
        """Test collecting from non-existent integration"""
        from datagod.scrapers.api_integration import APIIntegrationManager

        with patch("os.makedirs"):
            manager = APIIntegrationManager()

        data = manager.collect_data("nonexistent", {})
        assert data == []

    def test_collect_data_exception(self):
        """Test collecting when exception occurs"""
        from datagod.scrapers.api_integration import APIIntegrationManager

        with patch("os.makedirs"):
            manager = APIIntegrationManager()

        mock_integration = MagicMock()
        mock_integration.get_records = MagicMock(side_effect=Exception("Error"))

        manager.add_integration("error", mock_integration)

        data = manager.collect_data("error", {})
        assert data == []


class TestSaveIntegrationData:
    """Test save_integration_data method"""

    def test_save_integration_data(self):
        """Test saving integration data"""
        from datagod.scrapers.api_integration import APIIntegrationManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("os.makedirs"):
                manager = APIIntegrationManager()
                manager.base_dir = tmpdir

            data = [{"id": 1, "name": "Test"}]
            filepath = manager.save_integration_data("test", data)

            assert os.path.exists(filepath)

            with open(filepath, "r") as f:
                saved_data = json.load(f)

            assert saved_data == data

    def test_save_integration_data_filename_format(self):
        """Test saved file has correct format"""
        from datagod.scrapers.api_integration import APIIntegrationManager

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("os.makedirs"):
                manager = APIIntegrationManager()
                manager.base_dir = tmpdir

            filepath = manager.save_integration_data("my_api", [])

            filename = os.path.basename(filepath)
            assert filename.startswith("my_api_data_")
            assert filename.endswith(".json")


class TestMockAPIIntegration:
    """Test MockAPIIntegration class"""

    def test_mock_api_import(self):
        """Test MockAPIIntegration can be imported"""
        from datagod.scrapers.api_integration import MockAPIIntegration

        assert MockAPIIntegration is not None

    def test_mock_get_records(self):
        """Test mock get_records"""
        from datagod.scrapers.api_integration import (
            APIIntegrationConfig,
            MockAPIIntegration,
        )

        config = APIIntegrationConfig(name="mock", base_url="https://mock.com")

        integration = MockAPIIntegration(config)
        records = integration.get_records({})

        assert len(records) == 10
        for i, record in enumerate(records, 1):
            assert record["id"] == f"mock_{i}"
            assert "title" in record
            assert "amount" in record

    def test_mock_normalize_record(self):
        """Test mock normalize_record"""
        from datagod.scrapers.api_integration import (
            APIIntegrationConfig,
            MockAPIIntegration,
        )

        config = APIIntegrationConfig(name="mock", base_url="https://mock.com")

        integration = MockAPIIntegration(config)
        record = {
            "id": "mock_1",
            "title": "Test Record",
            "description": "Description",
            "amount": 1000.0,
            "date": "2023-01-01",
            "url": "https://example.com/1",
        }

        normalized = integration.normalize_record(record)

        assert normalized["source"] == "mock_api"
        assert normalized["source_id"] == "mock_1"
        assert normalized["title"] == "Test Record"
        assert normalized["jurisdiction"] == "Mock County, XX"
        assert "collected_at" in normalized


class TestCaliforniaPropertyAPI:
    """Test CaliforniaPropertyAPI class"""

    def test_california_api_import(self):
        """Test CaliforniaPropertyAPI can be imported"""
        from datagod.scrapers.api_integration import CaliforniaPropertyAPI

        assert CaliforniaPropertyAPI is not None

    def test_california_get_records(self):
        """Test California get_records"""
        from datagod.scrapers.api_integration import (
            APIIntegrationConfig,
            CaliforniaPropertyAPI,
        )

        config = APIIntegrationConfig(name="california", base_url="https://ca.gov")

        integration = CaliforniaPropertyAPI(config)
        records = integration.get_records({})

        assert len(records) == 5
        assert all("county" in r for r in records)
        assert all("address" in r for r in records)
        assert all("owner" in r for r in records)

    def test_california_normalize_record(self):
        """Test California normalize_record"""
        from datagod.scrapers.api_integration import (
            APIIntegrationConfig,
            CaliforniaPropertyAPI,
        )

        config = APIIntegrationConfig(name="california", base_url="https://ca.gov")

        integration = CaliforniaPropertyAPI(config)
        record = {
            "id": "ca_1",
            "county": "Los Angeles",
            "address": "123 Main St",
            "owner": "John Doe",
            "assessed_value": 500000,
            "last_sale_date": "2022-01-01",
            "property_type": "Single Family",
            "bedrooms": 3,
            "bathrooms": 2,
            "square_feet": 2000,
            "year_built": 2000,
        }

        normalized = integration.normalize_record(record)

        assert normalized["source"] == "california_property_api"
        assert "additional_data" in normalized
        assert normalized["additional_data"]["owner"] == "John Doe"


class TestTexasPropertyAPI:
    """Test TexasPropertyAPI class"""

    def test_texas_api_import(self):
        """Test TexasPropertyAPI can be imported"""
        from datagod.scrapers.api_integration import TexasPropertyAPI

        assert TexasPropertyAPI is not None

    def test_texas_get_records(self):
        """Test Texas get_records"""
        from datagod.scrapers.api_integration import (
            APIIntegrationConfig,
            TexasPropertyAPI,
        )

        config = APIIntegrationConfig(name="texas", base_url="https://tx.gov")

        integration = TexasPropertyAPI(config)
        records = integration.get_records({})

        assert len(records) == 5

    def test_texas_normalize_record(self):
        """Test Texas normalize_record"""
        from datagod.scrapers.api_integration import (
            APIIntegrationConfig,
            TexasPropertyAPI,
        )

        config = APIIntegrationConfig(name="texas", base_url="https://tx.gov")

        integration = TexasPropertyAPI(config)
        record = {
            "id": "tx_1",
            "county": "Harris",
            "address": "456 Oak Ave",
            "owner": "Jane Smith",
            "appraised_value": 400000,
            "last_sale_date": "2021-03-10",
            "property_type": "Single Family",
            "bedrooms": 4,
            "bathrooms": 3,
            "square_feet": 2200,
            "year_built": 2005,
        }

        normalized = integration.normalize_record(record)

        assert normalized["source"] == "texas_property_api"
        assert "additional_data" in normalized


class TestFloridaPropertyAPI:
    """Test FloridaPropertyAPI class"""

    def test_florida_api_import(self):
        """Test FloridaPropertyAPI can be imported"""
        from datagod.scrapers.api_integration import FloridaPropertyAPI

        assert FloridaPropertyAPI is not None

    def test_florida_get_records(self):
        """Test Florida get_records"""
        from datagod.scrapers.api_integration import (
            APIIntegrationConfig,
            FloridaPropertyAPI,
        )

        config = APIIntegrationConfig(name="florida", base_url="https://fl.gov")

        integration = FloridaPropertyAPI(config)
        records = integration.get_records({})

        assert len(records) == 5

    def test_florida_normalize_record(self):
        """Test Florida normalize_record"""
        from datagod.scrapers.api_integration import (
            APIIntegrationConfig,
            FloridaPropertyAPI,
        )

        config = APIIntegrationConfig(name="florida", base_url="https://fl.gov")

        integration = FloridaPropertyAPI(config)
        record = {
            "id": "fl_1",
            "county": "Miami-Dade",
            "address": "789 Palm St",
            "owner": "Robert Johnson",
            "assessed_value": 450000,
            "last_sale_date": "2020-11-05",
            "property_type": "Condominium",
            "bedrooms": 2,
            "bathrooms": 2,
            "square_feet": 1500,
            "year_built": 2010,
        }

        normalized = integration.normalize_record(record)

        assert normalized["source"] == "florida_property_api"
        assert "additional_data" in normalized


class TestMainFunction:
    """Test main function"""

    def test_main_runs(self):
        """Test main function executes"""
        from datagod.scrapers.api_integration import main

        with patch("os.makedirs"):
            with patch("builtins.print"):
                with patch("builtins.open", MagicMock()):
                    main()


class TestLogger:
    """Test logging configuration"""

    def test_logger_exists(self):
        """Test logger is configured"""
        from datagod.scrapers import api_integration

        assert hasattr(api_integration, "logger")
