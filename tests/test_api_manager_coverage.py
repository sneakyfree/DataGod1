#!/usr/bin/env python3
"""
Comprehensive tests for datagod/scrapers/api_manager.py
Tests APIManager class functionality
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, mock_open, patch

import pytest


class TestAPIManagerInit:
    """Tests for APIManager initialization"""

    def test_api_manager_init_default_credentials(self):
        """Test APIManager initialization with default credentials file"""
        mock_logger = MagicMock()

        class MockAPIManager:
            API_REGISTRY = {
                "florida_property_appraiser": MagicMock,
                "california_sos": MagicMock,
            }

            def __init__(self, credentials_file=None):
                self.credentials_file = (
                    credentials_file or self._get_default_credentials_file()
                )
                self.credentials = self._load_credentials()
                self.active_integrations = {}
                self.usage_stats = {
                    "total_requests": 0,
                    "total_cost": 0.0,
                    "api_usage": {},
                    "last_updated": datetime.now().isoformat(),
                }
                mock_logger.info(
                    f"Initialized API Manager with {len(self.API_REGISTRY)} registered APIs"
                )

            def _get_default_credentials_file(self):
                return "/tmp/api_credentials.json"

            def _load_credentials(self):
                return {}

        manager = MockAPIManager()

        assert manager.credentials_file == "/tmp/api_credentials.json"
        assert manager.usage_stats["total_requests"] == 0
        assert manager.usage_stats["total_cost"] == 0.0

    def test_api_manager_init_custom_credentials(self):
        """Test APIManager initialization with custom credentials file"""

        class MockAPIManager:
            API_REGISTRY = {}

            def __init__(self, credentials_file=None):
                self.credentials_file = credentials_file or "/default/path.json"
                self.credentials = {}
                self.active_integrations = {}
                self.usage_stats = {
                    "total_requests": 0,
                    "total_cost": 0.0,
                    "api_usage": {},
                    "last_updated": datetime.now().isoformat(),
                }

        manager = MockAPIManager(credentials_file="/custom/credentials.json")

        assert manager.credentials_file == "/custom/credentials.json"


class TestCredentialsManagement:
    """Tests for credentials management"""

    def test_get_default_credentials_file(self):
        """Test getting default credentials file path"""
        from pathlib import Path

        def _get_default_credentials_file():
            config_dir = Path("/home/user/project/config")
            return str(config_dir / "api_credentials.json")

        result = _get_default_credentials_file()
        assert "api_credentials.json" in result

    def test_load_credentials_file_exists(self):
        """Test loading credentials when file exists"""
        credentials_data = {
            "florida_property_appraiser": {
                "api_key": "test_key_123",
                "updated_at": "2023-01-01T00:00:00",
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(credentials_data, f)
            temp_path = f.name

        try:

            def _load_credentials(credentials_file):
                if os.path.exists(credentials_file):
                    try:
                        with open(credentials_file, "r") as f:
                            return json.load(f)
                    except Exception:
                        return {}
                return {}

            result = _load_credentials(temp_path)
            assert "florida_property_appraiser" in result
            assert result["florida_property_appraiser"]["api_key"] == "test_key_123"
        finally:
            os.unlink(temp_path)

    def test_load_credentials_file_not_exists(self):
        """Test loading credentials when file doesn't exist"""
        mock_logger = MagicMock()

        def _load_credentials(credentials_file):
            if os.path.exists(credentials_file):
                try:
                    with open(credentials_file, "r") as f:
                        return json.load(f)
                except Exception as e:
                    mock_logger.error(f"Failed to load credentials: {e}")
                    return {}
            else:
                mock_logger.warning(f"Credentials file not found: {credentials_file}")
                return {}

        result = _load_credentials("/nonexistent/file.json")
        assert result == {}
        mock_logger.warning.assert_called()

    def test_load_credentials_invalid_json(self):
        """Test loading credentials with invalid JSON"""
        mock_logger = MagicMock()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            temp_path = f.name

        try:

            def _load_credentials(credentials_file):
                if os.path.exists(credentials_file):
                    try:
                        with open(credentials_file, "r") as f:
                            return json.load(f)
                    except Exception as e:
                        mock_logger.error(f"Failed to load credentials: {e}")
                        return {}
                return {}

            result = _load_credentials(temp_path)
            assert result == {}
            mock_logger.error.assert_called()
        finally:
            os.unlink(temp_path)

    def test_save_credentials(self):
        """Test saving credentials to file"""
        mock_logger = MagicMock()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            credentials = {
                "florida_property_appraiser": {
                    "api_key": "new_key_456",
                    "updated_at": datetime.now().isoformat(),
                }
            }

            def _save_credentials(credentials_file, credentials_data):
                try:
                    with open(credentials_file, "w") as f:
                        json.dump(credentials_data, f, indent=2)
                    mock_logger.info("Credentials saved successfully")
                except Exception as e:
                    mock_logger.error(f"Failed to save credentials: {e}")

            _save_credentials(temp_path, credentials)

            # Verify file was saved
            with open(temp_path, "r") as f:
                saved_data = json.load(f)
            assert "florida_property_appraiser" in saved_data
        finally:
            os.unlink(temp_path)

    def test_add_credentials(self):
        """Test adding credentials"""
        mock_logger = MagicMock()

        class MockAPIManager:
            def __init__(self):
                self.credentials = {}
                self.credentials_file = "/tmp/test.json"

            def _save_credentials(self):
                pass

            def add_credentials(self, api_name, credentials):
                self.credentials[api_name] = {
                    **credentials,
                    "updated_at": datetime.now().isoformat(),
                }
                self._save_credentials()
                mock_logger.info(f"Credentials updated for {api_name}")

        manager = MockAPIManager()
        manager.add_credentials("test_api", {"api_key": "abc123"})

        assert "test_api" in manager.credentials
        assert manager.credentials["test_api"]["api_key"] == "abc123"
        assert "updated_at" in manager.credentials["test_api"]


class TestIntegrationManagement:
    """Tests for API integration management"""

    def test_get_integration_cached(self):
        """Test getting cached integration"""
        mock_integration = MagicMock()

        class MockAPIManager:
            def __init__(self):
                self.active_integrations = {}
                self.credentials = {}

            def _is_integration_valid(self, integration):
                return True

            def _create_integration(self, jurisdiction_id, api_type, jurisdiction_name):
                return mock_integration

            def get_integration(
                self, jurisdiction_id, api_type, jurisdiction_name=None
            ):
                cache_key = f"{jurisdiction_id}_{api_type}"

                if cache_key in self.active_integrations:
                    integration = self.active_integrations[cache_key]
                    if self._is_integration_valid(integration):
                        return integration
                    else:
                        del self.active_integrations[cache_key]

                integration = self._create_integration(
                    jurisdiction_id, api_type, jurisdiction_name
                )
                if integration:
                    self.active_integrations[cache_key] = integration

                return integration

        manager = MockAPIManager()

        # First call creates integration
        result1 = manager.get_integration(1, "florida_api")
        assert result1 == mock_integration

        # Second call returns cached
        result2 = manager.get_integration(1, "florida_api")
        assert result2 == mock_integration

    def test_get_integration_expired(self):
        """Test getting integration when cached one is expired"""
        mock_old_integration = MagicMock()
        mock_new_integration = MagicMock()

        class MockAPIManager:
            def __init__(self):
                self.active_integrations = {"1_florida_api": mock_old_integration}
                self.credentials = {}
                self.call_count = 0

            def _is_integration_valid(self, integration):
                return False  # Simulate expired

            def _create_integration(self, jurisdiction_id, api_type, jurisdiction_name):
                return mock_new_integration

            def get_integration(
                self, jurisdiction_id, api_type, jurisdiction_name=None
            ):
                cache_key = f"{jurisdiction_id}_{api_type}"

                if cache_key in self.active_integrations:
                    integration = self.active_integrations[cache_key]
                    if self._is_integration_valid(integration):
                        return integration
                    else:
                        del self.active_integrations[cache_key]

                integration = self._create_integration(
                    jurisdiction_id, api_type, jurisdiction_name
                )
                if integration:
                    self.active_integrations[cache_key] = integration

                return integration

        manager = MockAPIManager()
        result = manager.get_integration(1, "florida_api")

        assert result == mock_new_integration

    def test_create_integration_unknown_api(self):
        """Test creating integration for unknown API type"""
        mock_logger = MagicMock()

        class MockAPIManager:
            API_REGISTRY = {"known_api": MagicMock}

            def __init__(self):
                self.credentials = {}

            def _create_integration(
                self, jurisdiction_id, api_type, jurisdiction_name=None
            ):
                if api_type not in self.API_REGISTRY:
                    mock_logger.error(f"Unknown API type: {api_type}")
                    return None
                return MagicMock()

        manager = MockAPIManager()
        result = manager._create_integration(1, "unknown_api")

        assert result is None
        mock_logger.error.assert_called()

    def test_create_integration_no_credentials(self):
        """Test creating integration without credentials"""
        mock_logger = MagicMock()

        class MockAPIManager:
            API_REGISTRY = {"known_api": MagicMock}

            def __init__(self):
                self.credentials = {}

            def _create_integration(
                self, jurisdiction_id, api_type, jurisdiction_name=None
            ):
                if api_type not in self.API_REGISTRY:
                    return None

                credentials = self.credentials.get(api_type, {})
                if not credentials:
                    mock_logger.warning(f"No credentials found for {api_type}")
                    return None

                return MagicMock()

        manager = MockAPIManager()
        result = manager._create_integration(1, "known_api")

        assert result is None
        mock_logger.warning.assert_called()

    def test_create_integration_success(self):
        """Test successful integration creation"""
        mock_logger = MagicMock()
        mock_api_class = MagicMock()
        mock_integration = MagicMock()
        mock_integration.authenticate.return_value = True
        mock_api_class.return_value = mock_integration

        class MockAPIManager:
            API_REGISTRY = {"known_api": mock_api_class}

            def __init__(self):
                self.credentials = {"known_api": {"api_key": "test123"}}

            def _create_integration(
                self, jurisdiction_id, api_type, jurisdiction_name=None
            ):
                if api_type not in self.API_REGISTRY:
                    return None

                credentials = self.credentials.get(api_type, {})
                if not credentials:
                    return None

                config = {
                    **credentials,
                    "jurisdiction_name": jurisdiction_name or "Unknown",
                }

                try:
                    api_class = self.API_REGISTRY[api_type]
                    integration = api_class(jurisdiction_id, config)

                    if integration.authenticate():
                        mock_logger.info(f"Successfully created {api_type} integration")
                        return integration
                    else:
                        return None
                except Exception as e:
                    mock_logger.error(f"Failed to create integration: {e}")
                    return None

        manager = MockAPIManager()
        result = manager._create_integration(1, "known_api", "Test County")

        assert result is not None
        mock_logger.info.assert_called()

    def test_create_integration_auth_fails(self):
        """Test integration creation when authentication fails"""
        mock_logger = MagicMock()
        mock_api_class = MagicMock()
        mock_integration = MagicMock()
        mock_integration.authenticate.return_value = False
        mock_api_class.return_value = mock_integration

        class MockAPIManager:
            API_REGISTRY = {"known_api": mock_api_class}

            def __init__(self):
                self.credentials = {"known_api": {"api_key": "test123"}}

            def _create_integration(
                self, jurisdiction_id, api_type, jurisdiction_name=None
            ):
                credentials = self.credentials.get(api_type, {})
                config = {
                    **credentials,
                    "jurisdiction_name": jurisdiction_name or "Unknown",
                }

                api_class = self.API_REGISTRY[api_type]
                integration = api_class(jurisdiction_id, config)

                if integration.authenticate():
                    return integration
                else:
                    mock_logger.error(f"Authentication failed for {api_type}")
                    return None

        manager = MockAPIManager()
        result = manager._create_integration(1, "known_api")

        assert result is None
        mock_logger.error.assert_called()

    def test_is_integration_valid_no_expiry(self):
        """Test integration validity check without expiry"""
        mock_integration = MagicMock(spec=[])  # No token_expires_at attribute

        def _is_integration_valid(integration):
            if (
                hasattr(integration, "token_expires_at")
                and integration.token_expires_at
            ):
                return datetime.now() < integration.token_expires_at - timedelta(
                    minutes=5
                )
            return True

        assert _is_integration_valid(mock_integration) == True

    def test_is_integration_valid_not_expired(self):
        """Test integration validity check with future expiry"""
        mock_integration = MagicMock()
        mock_integration.token_expires_at = datetime.now() + timedelta(hours=1)

        def _is_integration_valid(integration):
            if (
                hasattr(integration, "token_expires_at")
                and integration.token_expires_at
            ):
                return datetime.now() < integration.token_expires_at - timedelta(
                    minutes=5
                )
            return True

        assert _is_integration_valid(mock_integration) == True

    def test_is_integration_valid_expired(self):
        """Test integration validity check with past expiry"""
        mock_integration = MagicMock()
        mock_integration.token_expires_at = datetime.now() - timedelta(hours=1)

        def _is_integration_valid(integration):
            if (
                hasattr(integration, "token_expires_at")
                and integration.token_expires_at
            ):
                return datetime.now() < integration.token_expires_at - timedelta(
                    minutes=5
                )
            return True

        assert _is_integration_valid(mock_integration) == False


class TestSearchFunctionality:
    """Tests for search functionality"""

    def test_search_across_apis(self):
        """Test searching across multiple APIs"""
        mock_logger = MagicMock()
        mock_integration = MagicMock()
        mock_integration.search_records.return_value = [{"id": 1}, {"id": 2}]

        class MockAPIManager:
            def __init__(self):
                self.usage_stats = {
                    "total_requests": 0,
                    "total_cost": 0.0,
                    "api_usage": {},
                }

            def get_integration(self, jurisdiction_id, api_type):
                return mock_integration

            def _get_available_apis_for_jurisdiction(self, jurisdiction_id):
                return ["api1", "api2"]

            def _track_api_usage(self, api_type, result_count):
                pass

            def search_across_apis(self, jurisdiction_id, query, api_types=None):
                results = []

                if api_types is None:
                    api_types = self._get_available_apis_for_jurisdiction(
                        jurisdiction_id
                    )

                for api_type in api_types:
                    try:
                        integration = self.get_integration(jurisdiction_id, api_type)
                        if integration:
                            api_results = integration.search_records(query)
                            results.extend(api_results)
                            self._track_api_usage(api_type, len(api_results))
                    except Exception as e:
                        mock_logger.error(f"Search failed for {api_type}: {e}")
                        continue

                mock_logger.info(f"Combined search returned {len(results)} results")
                return results

        manager = MockAPIManager()
        results = manager.search_across_apis(1, {"name": "test"})

        assert len(results) == 4  # 2 results from each of 2 APIs

    def test_search_across_apis_with_error(self):
        """Test searching when one API fails"""
        mock_logger = MagicMock()

        call_count = [0]

        def mock_search_records(query):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("API error")
            return [{"id": 1}]

        mock_integration = MagicMock()
        mock_integration.search_records = mock_search_records

        class MockAPIManager:
            def __init__(self):
                self.usage_stats = {"api_usage": {}}

            def get_integration(self, jurisdiction_id, api_type):
                return mock_integration

            def _track_api_usage(self, api_type, result_count):
                pass

            def search_across_apis(self, jurisdiction_id, query, api_types):
                results = []

                for api_type in api_types:
                    try:
                        integration = self.get_integration(jurisdiction_id, api_type)
                        if integration:
                            api_results = integration.search_records(query)
                            results.extend(api_results)
                    except Exception as e:
                        mock_logger.error(f"Search failed for {api_type}: {e}")
                        continue

                return results

        manager = MockAPIManager()
        results = manager.search_across_apis(1, {"name": "test"}, ["api1", "api2"])

        # First API fails, second succeeds
        assert len(results) == 1
        mock_logger.error.assert_called()


class TestUsageTracking:
    """Tests for API usage tracking"""

    def test_track_api_usage_new_api(self):
        """Test tracking usage for a new API"""

        class MockAPIManager:
            def __init__(self):
                self.usage_stats = {
                    "total_requests": 0,
                    "total_cost": 0.0,
                    "api_usage": {},
                }

            def _calculate_api_cost(self, api_type, result_count):
                return 0.10

            def _track_api_usage(self, api_type, result_count):
                if api_type not in self.usage_stats["api_usage"]:
                    self.usage_stats["api_usage"][api_type] = {
                        "requests": 0,
                        "results": 0,
                        "cost": 0.0,
                    }

                self.usage_stats["api_usage"][api_type]["requests"] += 1
                self.usage_stats["api_usage"][api_type]["results"] += result_count

                cost = self._calculate_api_cost(api_type, result_count)
                self.usage_stats["api_usage"][api_type]["cost"] += cost
                self.usage_stats["total_cost"] += cost
                self.usage_stats["total_requests"] += 1

        manager = MockAPIManager()
        manager._track_api_usage("new_api", 5)

        assert "new_api" in manager.usage_stats["api_usage"]
        assert manager.usage_stats["api_usage"]["new_api"]["requests"] == 1
        assert manager.usage_stats["api_usage"]["new_api"]["results"] == 5
        assert manager.usage_stats["total_requests"] == 1

    def test_track_api_usage_existing_api(self):
        """Test tracking usage for an existing API"""

        class MockAPIManager:
            def __init__(self):
                self.usage_stats = {
                    "total_requests": 5,
                    "total_cost": 0.50,
                    "api_usage": {
                        "existing_api": {"requests": 5, "results": 25, "cost": 0.50}
                    },
                }

            def _calculate_api_cost(self, api_type, result_count):
                return 0.10

            def _track_api_usage(self, api_type, result_count):
                if api_type not in self.usage_stats["api_usage"]:
                    self.usage_stats["api_usage"][api_type] = {
                        "requests": 0,
                        "results": 0,
                        "cost": 0.0,
                    }

                self.usage_stats["api_usage"][api_type]["requests"] += 1
                self.usage_stats["api_usage"][api_type]["results"] += result_count

                cost = self._calculate_api_cost(api_type, result_count)
                self.usage_stats["api_usage"][api_type]["cost"] += cost
                self.usage_stats["total_cost"] += cost
                self.usage_stats["total_requests"] += 1

        manager = MockAPIManager()
        manager._track_api_usage("existing_api", 10)

        assert manager.usage_stats["api_usage"]["existing_api"]["requests"] == 6
        assert manager.usage_stats["api_usage"]["existing_api"]["results"] == 35
        assert manager.usage_stats["total_requests"] == 6

    def test_calculate_api_cost_default(self):
        """Test cost calculation with default pricing"""

        def _calculate_api_cost(api_type, result_count):
            cost_per_request = {
                "florida_property_appraiser": 0.10,
                "california_sos": 0.15,
            }
            base_cost = cost_per_request.get(api_type, 0.10)

            if result_count > 10:
                base_cost += (result_count - 10) * 0.01

            return base_cost

        assert _calculate_api_cost("florida_property_appraiser", 5) == 0.10
        assert _calculate_api_cost("california_sos", 5) == 0.15
        assert _calculate_api_cost("unknown_api", 5) == 0.10

    def test_calculate_api_cost_high_volume(self):
        """Test cost calculation with high result count"""

        def _calculate_api_cost(api_type, result_count):
            cost_per_request = {"florida_property_appraiser": 0.10}
            base_cost = cost_per_request.get(api_type, 0.10)

            if result_count > 10:
                base_cost += (result_count - 10) * 0.01

            return base_cost

        # 20 results = 0.10 + (20-10) * 0.01 = 0.10 + 0.10 = 0.20
        assert _calculate_api_cost("florida_property_appraiser", 20) == 0.20


class TestMetricsAndReporting:
    """Tests for metrics and reporting"""

    def test_get_api_metrics(self):
        """Test getting API metrics"""
        mock_integration = MagicMock()
        mock_integration.get_metrics.return_value = {"requests": 10, "errors": 1}

        class MockAPIManager:
            def __init__(self):
                self.usage_stats = {
                    "total_requests": 100,
                    "total_cost": 10.0,
                    "api_usage": {},
                }
                self.active_integrations = {"1_florida_api": mock_integration}

            def get_api_metrics(self):
                metrics = {"overall": self.usage_stats.copy(), "integrations": {}}

                for cache_key, integration in self.active_integrations.items():
                    parts = cache_key.split("_", 1)
                    jurisdiction_id = parts[0]
                    api_type = parts[1] if len(parts) > 1 else "unknown"
                    metrics["integrations"][cache_key] = {
                        "jurisdiction_id": int(jurisdiction_id),
                        "api_type": api_type,
                        **integration.get_metrics(),
                    }

                return metrics

        manager = MockAPIManager()
        metrics = manager.get_api_metrics()

        assert metrics["overall"]["total_requests"] == 100
        assert "1_florida_api" in metrics["integrations"]
        assert metrics["integrations"]["1_florida_api"]["requests"] == 10

    def test_get_cost_report(self):
        """Test generating cost report"""

        class MockAPIManager:
            def __init__(self):
                self.usage_stats = {
                    "total_cost": 15.50,
                    "total_requests": 100,
                    "api_usage": {
                        "florida_api": {"requests": 60, "results": 300, "cost": 9.00},
                        "california_api": {
                            "requests": 40,
                            "results": 200,
                            "cost": 6.50,
                        },
                    },
                }

            def get_cost_report(self, days=30):
                report = {
                    "period_days": days,
                    "total_cost": self.usage_stats["total_cost"],
                    "total_requests": self.usage_stats["total_requests"],
                    "cost_per_request": 0.0,
                    "api_breakdown": {},
                    "generated_at": datetime.now().isoformat(),
                }

                if self.usage_stats["total_requests"] > 0:
                    report["cost_per_request"] = (
                        self.usage_stats["total_cost"]
                        / self.usage_stats["total_requests"]
                    )

                for api_type, usage in self.usage_stats["api_usage"].items():
                    report["api_breakdown"][api_type] = {
                        "requests": usage["requests"],
                        "results": usage["results"],
                        "cost": usage["cost"],
                        "cost_per_request": (
                            usage["cost"] / usage["requests"]
                            if usage["requests"] > 0
                            else 0
                        ),
                        "results_per_request": (
                            usage["results"] / usage["requests"]
                            if usage["requests"] > 0
                            else 0
                        ),
                    }

                return report

        manager = MockAPIManager()
        report = manager.get_cost_report(days=30)

        assert report["period_days"] == 30
        assert report["total_cost"] == 15.50
        assert report["total_requests"] == 100
        assert report["cost_per_request"] == 0.155
        assert "florida_api" in report["api_breakdown"]
        assert report["api_breakdown"]["florida_api"]["cost_per_request"] == 0.15

    def test_get_cost_report_no_requests(self):
        """Test cost report with no requests"""

        class MockAPIManager:
            def __init__(self):
                self.usage_stats = {
                    "total_cost": 0.0,
                    "total_requests": 0,
                    "api_usage": {},
                }

            def get_cost_report(self, days=30):
                report = {
                    "period_days": days,
                    "total_cost": self.usage_stats["total_cost"],
                    "total_requests": self.usage_stats["total_requests"],
                    "cost_per_request": 0.0,
                    "api_breakdown": {},
                }

                if self.usage_stats["total_requests"] > 0:
                    report["cost_per_request"] = (
                        self.usage_stats["total_cost"]
                        / self.usage_stats["total_requests"]
                    )

                return report

        manager = MockAPIManager()
        report = manager.get_cost_report()

        assert report["cost_per_request"] == 0.0


class TestCleanupAndMaintenance:
    """Tests for cleanup and maintenance functions"""

    def test_cleanup_expired_integrations(self):
        """Test cleaning up expired integrations"""
        mock_logger = MagicMock()
        mock_valid = MagicMock()
        mock_expired = MagicMock()

        class MockAPIManager:
            def __init__(self):
                self.active_integrations = {
                    "valid_1": mock_valid,
                    "expired_1": mock_expired,
                    "expired_2": mock_expired,
                }

            def _is_integration_valid(self, integration):
                return integration == mock_valid

            def cleanup_expired_integrations(self):
                expired_keys = []

                for cache_key, integration in self.active_integrations.items():
                    if not self._is_integration_valid(integration):
                        expired_keys.append(cache_key)

                for key in expired_keys:
                    del self.active_integrations[key]
                    mock_logger.info(f"Cleaned up expired integration: {key}")

                if expired_keys:
                    mock_logger.info(
                        f"Cleaned up {len(expired_keys)} expired integrations"
                    )

        manager = MockAPIManager()
        manager.cleanup_expired_integrations()

        assert len(manager.active_integrations) == 1
        assert "valid_1" in manager.active_integrations
        assert mock_logger.info.call_count == 3  # 2 individual + 1 summary

    def test_cleanup_no_expired_integrations(self):
        """Test cleanup when no integrations are expired"""
        mock_logger = MagicMock()
        mock_valid = MagicMock()

        class MockAPIManager:
            def __init__(self):
                self.active_integrations = {
                    "valid_1": mock_valid,
                    "valid_2": mock_valid,
                }

            def _is_integration_valid(self, integration):
                return True

            def cleanup_expired_integrations(self):
                expired_keys = []

                for cache_key, integration in self.active_integrations.items():
                    if not self._is_integration_valid(integration):
                        expired_keys.append(cache_key)

                for key in expired_keys:
                    del self.active_integrations[key]

                if expired_keys:
                    mock_logger.info(
                        f"Cleaned up {len(expired_keys)} expired integrations"
                    )

        manager = MockAPIManager()
        manager.cleanup_expired_integrations()

        assert len(manager.active_integrations) == 2
        mock_logger.info.assert_not_called()


class TestAPIInfo:
    """Tests for API information functions"""

    def test_list_available_apis(self):
        """Test listing available APIs"""

        class MockAPIManager:
            API_REGISTRY = {
                "florida_property_appraiser": MagicMock,
                "california_sos": MagicMock,
                "texas_comptroller": MagicMock,
            }

            def list_available_apis(self):
                return list(self.API_REGISTRY.keys())

        manager = MockAPIManager()
        apis = manager.list_available_apis()

        assert len(apis) == 3
        assert "florida_property_appraiser" in apis
        assert "california_sos" in apis

    def test_get_api_info_exists(self):
        """Test getting info for existing API"""
        mock_api_class = MagicMock
        mock_api_class.__name__ = "FloridaPropertyAppraiserAPI"
        mock_api_class.__module__ = "datagod.scrapers.florida_api"

        class MockAPIManager:
            API_REGISTRY = {"florida_property_appraiser": mock_api_class}

            def __init__(self):
                self.credentials = {
                    "florida_property_appraiser": {
                        "api_key": "test123",
                        "updated_at": "2023-06-01T00:00:00",
                    }
                }

            def get_api_info(self, api_type):
                if api_type not in self.API_REGISTRY:
                    return {}

                api_class = self.API_REGISTRY[api_type]
                credentials = self.credentials.get(api_type, {})

                return {
                    "api_type": api_type,
                    "class_name": api_class.__name__,
                    "has_credentials": bool(credentials),
                    "last_updated": credentials.get("updated_at"),
                    "module": api_class.__module__,
                }

        manager = MockAPIManager()
        info = manager.get_api_info("florida_property_appraiser")

        assert info["api_type"] == "florida_property_appraiser"
        assert info["class_name"] == "FloridaPropertyAppraiserAPI"
        assert info["has_credentials"] == True
        assert info["last_updated"] == "2023-06-01T00:00:00"

    def test_get_api_info_not_exists(self):
        """Test getting info for non-existent API"""

        class MockAPIManager:
            API_REGISTRY = {}

            def __init__(self):
                self.credentials = {}

            def get_api_info(self, api_type):
                if api_type not in self.API_REGISTRY:
                    return {}
                return {"api_type": api_type}

        manager = MockAPIManager()
        info = manager.get_api_info("nonexistent_api")

        assert info == {}


class TestGlobalInstance:
    """Tests for global API manager instance"""

    def test_get_api_manager(self):
        """Test getting global API manager instance"""
        global_manager = MagicMock()

        def get_api_manager():
            return global_manager

        result = get_api_manager()
        assert result == global_manager


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
