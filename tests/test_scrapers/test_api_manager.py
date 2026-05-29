"""
Tests for datagod/scrapers/api_manager.py

Comprehensive tests for the API Manager module.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest


class TestAPIManagerInitialization:
    """Tests for APIManager initialization"""

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_init_no_credentials_file(self, mock_exists):
        """Test initialization when credentials file doesn't exist"""
        mock_exists.return_value = False

        # Import after patching to avoid import errors
        from datagod.scrapers.api_manager import APIManager

        manager = APIManager(credentials_file="/tmp/nonexistent.json")

        assert manager.credentials == {}
        assert manager.active_integrations == {}
        assert manager.usage_stats["total_requests"] == 0
        assert manager.usage_stats["total_cost"] == 0.0

    @patch("builtins.open", mock_open(read_data='{"api_key": "test123"}'))
    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_init_with_credentials_file(self, mock_exists):
        """Test initialization with existing credentials file"""
        mock_exists.return_value = True

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager(credentials_file="/tmp/creds.json")

        assert manager.credentials == {"api_key": "test123"}

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_init_with_invalid_json(self, mock_exists):
        """Test initialization with invalid JSON credentials"""
        mock_exists.return_value = True

        with patch("builtins.open", mock_open(read_data="invalid json{")):
            from datagod.scrapers.api_manager import APIManager

            manager = APIManager(credentials_file="/tmp/bad.json")
            assert manager.credentials == {}


class TestCredentialsManagement:
    """Tests for credentials management"""

    def test_add_credentials(self, tmp_path):
        """Test adding credentials"""
        from datagod.scrapers.api_manager import APIManager

        creds_file = tmp_path / "creds.json"
        manager = APIManager(credentials_file=str(creds_file))

        manager.add_credentials("test_api", {"key": "value123"})

        assert "test_api" in manager.credentials
        assert manager.credentials["test_api"]["key"] == "value123"
        assert "updated_at" in manager.credentials["test_api"]

    def test_add_credentials_overwrites_existing(self, tmp_path):
        """Test that adding credentials overwrites existing ones"""
        from datagod.scrapers.api_manager import APIManager

        creds_file = tmp_path / "creds.json"
        manager = APIManager(credentials_file=str(creds_file))

        manager.add_credentials("test_api", {"key": "old_value"})
        manager.add_credentials("test_api", {"key": "new_value"})

        assert manager.credentials["test_api"]["key"] == "new_value"


class TestIntegrationManagement:
    """Tests for API integration management"""

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_get_integration_unknown_type(self, mock_exists):
        """Test getting integration with unknown API type"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()
        integration = manager.get_integration(1, "unknown_api_type")

        assert integration is None

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_get_integration_no_credentials(self, mock_exists):
        """Test getting integration without credentials"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()
        # Use a registered API type but without credentials
        integration = manager.get_integration(1, "florida_property_appraiser")

        assert integration is None

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_is_integration_valid_no_expiry(self, mock_exists):
        """Test integration validity check without token expiry"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()
        mock_integration = Mock(spec=[])  # No token_expires_at attribute

        assert manager._is_integration_valid(mock_integration) is True

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_is_integration_valid_not_expired(self, mock_exists):
        """Test integration validity with valid token"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()
        mock_integration = Mock()
        mock_integration.token_expires_at = datetime.now() + timedelta(hours=1)

        assert manager._is_integration_valid(mock_integration) is True

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_is_integration_valid_expired(self, mock_exists):
        """Test integration validity with expired token"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()
        mock_integration = Mock()
        mock_integration.token_expires_at = datetime.now() - timedelta(hours=1)

        assert manager._is_integration_valid(mock_integration) is False


class TestSearchAcrossAPIs:
    """Tests for cross-API search functionality"""

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_search_across_apis_no_results(self, mock_exists):
        """Test search across APIs with no results"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()
        results = manager.search_across_apis(1, {"query": "test"}, api_types=[])

        assert results == []

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_get_available_apis_for_jurisdiction(self, mock_exists):
        """Test getting available APIs for jurisdiction"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()
        apis = manager._get_available_apis_for_jurisdiction(1)

        assert isinstance(apis, list)
        assert len(apis) > 0


class TestUsageTracking:
    """Tests for API usage tracking"""

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_track_api_usage_new_api(self, mock_exists):
        """Test tracking usage for a new API"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()
        manager._track_api_usage("test_api", 10)

        assert "test_api" in manager.usage_stats["api_usage"]
        assert manager.usage_stats["api_usage"]["test_api"]["requests"] == 1
        assert manager.usage_stats["api_usage"]["test_api"]["results"] == 10
        assert manager.usage_stats["total_requests"] == 1

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_track_api_usage_existing_api(self, mock_exists):
        """Test tracking usage for existing API"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()
        manager._track_api_usage("test_api", 5)
        manager._track_api_usage("test_api", 10)

        assert manager.usage_stats["api_usage"]["test_api"]["requests"] == 2
        assert manager.usage_stats["api_usage"]["test_api"]["results"] == 15
        assert manager.usage_stats["total_requests"] == 2

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_calculate_api_cost_known_api(self, mock_exists):
        """Test cost calculation for known API"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()
        cost = manager._calculate_api_cost("florida_property_appraiser", 5)

        assert cost == 0.10  # Base cost for Florida API

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_calculate_api_cost_high_volume(self, mock_exists):
        """Test cost calculation for high volume requests"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()
        cost = manager._calculate_api_cost("florida_property_appraiser", 20)

        # Base 0.10 + (20-10) * 0.01 = 0.20
        assert cost == 0.20

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_calculate_api_cost_unknown_api(self, mock_exists):
        """Test cost calculation for unknown API uses default"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()
        cost = manager._calculate_api_cost("unknown_api", 5)

        assert cost == 0.10  # Default cost


class TestMetricsAndReports:
    """Tests for metrics and cost reporting"""

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_get_api_metrics_empty(self, mock_exists):
        """Test getting metrics with no activity"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()
        metrics = manager.get_api_metrics()

        assert "overall" in metrics
        assert "integrations" in metrics
        assert metrics["overall"]["total_requests"] == 0

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_get_cost_report_no_usage(self, mock_exists):
        """Test cost report with no usage"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()
        report = manager.get_cost_report()

        assert report["total_cost"] == 0.0
        assert report["total_requests"] == 0
        assert report["cost_per_request"] == 0.0

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_get_cost_report_with_usage(self, mock_exists):
        """Test cost report with usage"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()
        manager._track_api_usage("florida_property_appraiser", 5)
        manager._track_api_usage("california_sos", 10)

        report = manager.get_cost_report()

        assert report["total_requests"] == 2
        assert report["total_cost"] > 0
        assert "api_breakdown" in report


class TestCleanupAndListing:
    """Tests for cleanup and listing functionality"""

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_cleanup_expired_integrations_none(self, mock_exists):
        """Test cleanup with no expired integrations"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()
        manager.cleanup_expired_integrations()

        # Should not raise any errors

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_cleanup_expired_integrations_some_expired(self, mock_exists):
        """Test cleanup removes expired integrations"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()

        # Add mock integrations
        valid_integration = Mock()
        valid_integration.token_expires_at = datetime.now() + timedelta(hours=1)

        expired_integration = Mock()
        expired_integration.token_expires_at = datetime.now() - timedelta(hours=1)

        manager.active_integrations["valid_key"] = valid_integration
        manager.active_integrations["expired_key"] = expired_integration

        manager.cleanup_expired_integrations()

        assert "valid_key" in manager.active_integrations
        assert "expired_key" not in manager.active_integrations

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_list_available_apis(self, mock_exists):
        """Test listing available APIs"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()
        apis = manager.list_available_apis()

        assert isinstance(apis, list)
        # Should have registered APIs
        assert len(apis) >= 0

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_get_api_info_unknown(self, mock_exists):
        """Test getting info for unknown API"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()
        info = manager.get_api_info("unknown_api")

        assert info == {}


class TestGlobalAPIManager:
    """Tests for global API manager instance"""

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_get_api_manager(self, mock_exists):
        """Test getting global API manager instance"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager, get_api_manager

        manager = get_api_manager()

        assert isinstance(manager, APIManager)


class TestAPIManagerCachedIntegration:
    """Tests for cached integration handling"""

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_get_integration_returns_cached_if_valid(self, mock_exists):
        """Test that get_integration returns cached integration if valid"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()

        # Create a mock integration
        mock_integration = Mock()
        mock_integration.token_expires_at = datetime.now() + timedelta(hours=1)

        # Add to cache
        manager.active_integrations["1_test_api"] = mock_integration

        # Should return the cached one
        result = manager.get_integration(1, "test_api")
        assert result is mock_integration

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_get_integration_removes_invalid_cache(self, mock_exists):
        """Test that get_integration removes invalid cached integration"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()

        # Create an expired mock integration
        mock_integration = Mock()
        mock_integration.token_expires_at = datetime.now() - timedelta(hours=1)

        # Add to cache
        manager.active_integrations["1_florida_property_appraiser"] = mock_integration

        # Should remove the invalid integration and return None (no credentials)
        result = manager.get_integration(1, "florida_property_appraiser")
        assert "1_florida_property_appraiser" not in manager.active_integrations


class TestAPIManagerCreateIntegration:
    """Tests for integration creation"""

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_create_integration_success(self, mock_exists):
        """Test successful integration creation"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()

        # Create a mock API class
        mock_api_class = Mock()
        mock_instance = Mock()
        mock_instance.authenticate.return_value = True
        mock_api_class.return_value = mock_instance

        # Register it
        manager._get_api_registry()["test_api"] = mock_api_class

        # Add credentials
        manager.credentials["test_api"] = {"api_key": "test123"}

        # Create integration
        integration = manager._create_integration(1, "test_api", "Test Jurisdiction")

        assert integration is mock_instance
        mock_api_class.assert_called_once()
        mock_instance.authenticate.assert_called_once()

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_create_integration_auth_fails(self, mock_exists):
        """Test integration creation when auth fails"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()

        # Create a mock API class that fails auth
        mock_api_class = Mock()
        mock_instance = Mock()
        mock_instance.authenticate.return_value = False
        mock_api_class.return_value = mock_instance

        # Register it
        manager._get_api_registry()["test_api"] = mock_api_class

        # Add credentials
        manager.credentials["test_api"] = {"api_key": "test123"}

        # Create integration should fail
        integration = manager._create_integration(1, "test_api")

        assert integration is None

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_create_integration_exception(self, mock_exists):
        """Test integration creation handles exceptions"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()

        # Create a mock API class that raises exception
        mock_api_class = Mock(side_effect=Exception("API Error"))

        # Register it
        manager._get_api_registry()["test_api"] = mock_api_class

        # Add credentials
        manager.credentials["test_api"] = {"api_key": "test123"}

        # Create integration should handle exception
        integration = manager._create_integration(1, "test_api")

        assert integration is None


class TestAPIManagerSearchWithResults:
    """Tests for search with actual results"""

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_search_across_apis_with_results(self, mock_exists):
        """Test search across APIs with actual results"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()

        # Create mock integration with results
        mock_integration = Mock()
        mock_integration.search_records.return_value = [
            {"id": 1, "name": "Test Record 1"},
            {"id": 2, "name": "Test Record 2"},
        ]
        mock_integration.token_expires_at = datetime.now() + timedelta(hours=1)

        # Add to active integrations
        manager.active_integrations["1_test_api"] = mock_integration

        # Perform search
        results = manager.search_across_apis(
            1, {"query": "test"}, api_types=["test_api"]
        )

        assert len(results) == 2
        assert results[0]["id"] == 1
        mock_integration.search_records.assert_called_once()

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_search_across_apis_with_exception(self, mock_exists):
        """Test search handles exceptions gracefully"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()

        # Create mock integration that raises exception
        mock_integration = Mock()
        mock_integration.search_records.side_effect = Exception("Search failed")
        mock_integration.token_expires_at = datetime.now() + timedelta(hours=1)

        # Add to active integrations
        manager.active_integrations["1_test_api"] = mock_integration

        # Perform search - should not raise
        results = manager.search_across_apis(
            1, {"query": "test"}, api_types=["test_api"]
        )

        assert results == []

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_search_across_apis_auto_detect(self, mock_exists):
        """Test search auto-detects available APIs"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()

        # Search without specifying api_types
        results = manager.search_across_apis(1, {"query": "test"})

        # Should not raise and return empty list (no active integrations)
        assert isinstance(results, list)


class TestAPIManagerGetApiInfo:
    """Tests for get_api_info with known APIs"""

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_get_api_info_known_api(self, mock_exists):
        """Test getting info for a known API"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()

        # Create a mock API class
        class MockAPIClass:
            pass

        # Register it
        manager._get_api_registry()["test_api"] = MockAPIClass

        # Add credentials
        manager.credentials["test_api"] = {
            "api_key": "test123",
            "updated_at": "2023-01-01T00:00:00",
        }

        info = manager.get_api_info("test_api")

        assert info["api_type"] == "test_api"
        assert info["class_name"] == "MockAPIClass"
        assert info["has_credentials"] is True
        assert info["last_updated"] == "2023-01-01T00:00:00"


class TestAPIManagerGetMetricsWithIntegrations:
    """Tests for get_api_metrics with active integrations"""

    @patch("datagod.scrapers.api_manager.os.path.exists")
    def test_get_api_metrics_with_integrations(self, mock_exists):
        """Test getting metrics with active integrations"""
        mock_exists.return_value = False

        from datagod.scrapers.api_manager import APIManager

        manager = APIManager()

        # Create mock integration with metrics
        mock_integration = Mock()
        mock_integration.get_metrics.return_value = {"requests": 10, "errors": 1}

        # Add to active integrations
        manager.active_integrations["1_test_api"] = mock_integration

        metrics = manager.get_api_metrics()

        assert "1_test_api" in metrics["integrations"]
        assert metrics["integrations"]["1_test_api"]["jurisdiction_id"] == 1
        assert metrics["integrations"]["1_test_api"]["api_type"] == "test_api"
        assert metrics["integrations"]["1_test_api"]["requests"] == 10


class TestAPIManagerSaveCredentials:
    """Tests for credentials saving with error handling"""

    def test_save_credentials_write_error(self, tmp_path):
        """Test save credentials handles write errors"""
        from datagod.scrapers.api_manager import APIManager

        # Use a path that will fail to write
        creds_file = tmp_path / "creds.json"
        manager = APIManager(credentials_file=str(creds_file))

        # Make the directory read-only to cause write failure
        import stat

        creds_file.touch()
        os.chmod(str(creds_file), stat.S_IRUSR)

        try:
            # This should not raise, just log error
            manager._save_credentials()
        finally:
            # Restore permissions
            os.chmod(str(creds_file), stat.S_IWUSR | stat.S_IRUSR)
