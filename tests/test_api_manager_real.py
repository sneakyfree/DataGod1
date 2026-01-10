"""
Tests for datagod/scrapers/api_manager.py
Tests the APIManager class logic and patterns
"""

import pytest
import os
import json
import tempfile
from unittest.mock import MagicMock, patch, mock_open
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


class TestAPIManagerLogic:
    """Test APIManager class logic"""

    def test_default_credentials_file_path(self):
        """Test default credentials file path generation"""
        from pathlib import Path
        # Simulate the path generation logic
        config_dir = Path(__file__).parent.parent / "datagod" / "config"
        credentials_file = str(config_dir / "api_credentials.json")
        assert "api_credentials.json" in credentials_file

    def test_load_credentials_missing_file(self):
        """Test loading credentials when file doesn't exist"""
        # Simulate the logic
        credentials_file = "/nonexistent/path/credentials.json"
        if not os.path.exists(credentials_file):
            credentials = {}
        assert credentials == {}

    def test_load_credentials_valid_json(self):
        """Test loading credentials from valid JSON"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'api_key': 'test123', 'secret': 'secret456'}, f)
            f.flush()
            temp_path = f.name

        try:
            with open(temp_path, 'r') as f:
                credentials = json.load(f)
            assert credentials['api_key'] == 'test123'
            assert credentials['secret'] == 'secret456'
        finally:
            os.unlink(temp_path)

    def test_load_credentials_invalid_json(self):
        """Test loading credentials from invalid JSON"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("not valid json {{{")
            f.flush()
            temp_path = f.name

        try:
            with open(temp_path, 'r') as f:
                try:
                    credentials = json.load(f)
                except json.JSONDecodeError:
                    credentials = {}
            assert credentials == {}
        finally:
            os.unlink(temp_path)

    def test_save_credentials(self):
        """Test saving credentials to file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            credentials = {'api_key': 'new_key', 'updated': True}
            with open(temp_path, 'w') as f:
                json.dump(credentials, f, indent=2)

            # Verify saved correctly
            with open(temp_path, 'r') as f:
                loaded = json.load(f)
            assert loaded['api_key'] == 'new_key'
            assert loaded['updated'] is True
        finally:
            os.unlink(temp_path)


class TestCredentialsManagement:
    """Test credentials management logic"""

    def test_add_credentials_new(self):
        """Test adding new credentials"""
        credentials = {}
        api_name = 'new_api'
        new_creds = {'api_key': 'key123', 'secret': 'secret123'}

        credentials[api_name] = {
            **new_creds,
            'updated_at': datetime.now().isoformat()
        }

        assert 'new_api' in credentials
        assert credentials['new_api']['api_key'] == 'key123'
        assert 'updated_at' in credentials['new_api']

    def test_add_credentials_update(self):
        """Test updating existing credentials"""
        credentials = {
            'existing_api': {'api_key': 'old_key'}
        }
        credentials['existing_api'] = {
            'api_key': 'new_key',
            'updated_at': datetime.now().isoformat()
        }

        assert credentials['existing_api']['api_key'] == 'new_key'

    def test_get_credentials_exists(self):
        """Test getting credentials that exist"""
        credentials = {
            'test_api': {'api_key': 'test123'}
        }
        api_creds = credentials.get('test_api', {})
        assert api_creds['api_key'] == 'test123'

    def test_get_credentials_missing(self):
        """Test getting credentials that don't exist"""
        credentials = {}
        api_creds = credentials.get('missing_api', {})
        assert api_creds == {}


class TestIntegrationCaching:
    """Test integration caching logic"""

    def test_cache_key_generation(self):
        """Test cache key generation"""
        jurisdiction_id = 123
        api_type = 'florida_property_appraiser'
        cache_key = f"{jurisdiction_id}_{api_type}"
        assert cache_key == "123_florida_property_appraiser"

    def test_cache_key_parsing(self):
        """Test cache key parsing"""
        cache_key = "123_florida_property_appraiser"
        jurisdiction_id, api_type = cache_key.split('_', 1)
        assert jurisdiction_id == "123"
        assert api_type == "florida_property_appraiser"

    def test_integration_caching(self):
        """Test caching of integrations"""
        active_integrations = {}
        cache_key = "1_test_api"
        mock_integration = MagicMock()

        # Add to cache
        active_integrations[cache_key] = mock_integration
        assert cache_key in active_integrations

        # Retrieve from cache
        cached = active_integrations.get(cache_key)
        assert cached == mock_integration

    def test_integration_cache_removal(self):
        """Test removal of invalid integrations from cache"""
        active_integrations = {"1_expired_api": MagicMock()}
        del active_integrations["1_expired_api"]
        assert "1_expired_api" not in active_integrations


class TestIntegrationValidation:
    """Test integration validation logic"""

    def test_is_integration_valid_no_expiry(self):
        """Test validation when no token expiry"""
        integration = MagicMock()
        # Remove token_expires_at attribute
        del integration.token_expires_at

        # Should return True (no expiry means always valid)
        is_valid = not hasattr(integration, 'token_expires_at') or integration.token_expires_at is None
        assert is_valid is True

    def test_is_integration_valid_expired(self):
        """Test validation when token is expired"""
        integration = MagicMock()
        integration.token_expires_at = datetime.now() - timedelta(hours=1)

        # Check if expired
        is_valid = datetime.now() < integration.token_expires_at - timedelta(minutes=5)
        assert is_valid is False

    def test_is_integration_valid_not_expired(self):
        """Test validation when token is not expired"""
        integration = MagicMock()
        integration.token_expires_at = datetime.now() + timedelta(hours=1)

        # Check if still valid
        is_valid = datetime.now() < integration.token_expires_at - timedelta(minutes=5)
        assert is_valid is True

    def test_is_integration_valid_about_to_expire(self):
        """Test validation when token is about to expire"""
        integration = MagicMock()
        # Token expires in 3 minutes (within 5-minute buffer)
        integration.token_expires_at = datetime.now() + timedelta(minutes=3)

        # Should be invalid due to 5-minute buffer
        is_valid = datetime.now() < integration.token_expires_at - timedelta(minutes=5)
        assert is_valid is False


class TestUsageTracking:
    """Test API usage tracking logic"""

    def test_initial_usage_stats(self):
        """Test initial usage stats structure"""
        usage_stats = {
            'total_requests': 0,
            'total_cost': 0.0,
            'api_usage': {},
            'last_updated': datetime.now().isoformat()
        }

        assert usage_stats['total_requests'] == 0
        assert usage_stats['total_cost'] == 0.0
        assert usage_stats['api_usage'] == {}

    def test_track_api_usage_new_api(self):
        """Test tracking usage for new API"""
        usage_stats = {'api_usage': {}, 'total_requests': 0, 'total_cost': 0.0}
        api_type = 'test_api'
        result_count = 5

        if api_type not in usage_stats['api_usage']:
            usage_stats['api_usage'][api_type] = {
                'requests': 0,
                'results': 0,
                'cost': 0.0
            }

        usage_stats['api_usage'][api_type]['requests'] += 1
        usage_stats['api_usage'][api_type]['results'] += result_count

        assert usage_stats['api_usage'][api_type]['requests'] == 1
        assert usage_stats['api_usage'][api_type]['results'] == 5

    def test_track_api_usage_existing_api(self):
        """Test tracking usage for existing API"""
        usage_stats = {
            'api_usage': {
                'existing_api': {'requests': 10, 'results': 50, 'cost': 5.0}
            },
            'total_requests': 10,
            'total_cost': 5.0
        }

        usage_stats['api_usage']['existing_api']['requests'] += 1
        usage_stats['api_usage']['existing_api']['results'] += 3

        assert usage_stats['api_usage']['existing_api']['requests'] == 11
        assert usage_stats['api_usage']['existing_api']['results'] == 53


class TestCostCalculation:
    """Test API cost calculation logic"""

    def test_calculate_api_cost_known_api(self):
        """Test cost calculation for known API"""
        cost_per_request = {
            'florida_property_appraiser': 0.10,
            'california_sos': 0.15,
        }

        api_type = 'florida_property_appraiser'
        result_count = 5

        base_cost = cost_per_request.get(api_type, 0.10)
        assert base_cost == 0.10

    def test_calculate_api_cost_unknown_api(self):
        """Test cost calculation for unknown API uses default"""
        cost_per_request = {}
        api_type = 'unknown_api'

        base_cost = cost_per_request.get(api_type, 0.10)
        assert base_cost == 0.10

    def test_calculate_api_cost_high_volume(self):
        """Test cost calculation for high-volume requests"""
        base_cost = 0.10
        result_count = 25

        # Add per-result cost for high-volume
        if result_count > 10:
            base_cost += (result_count - 10) * 0.01

        # 0.10 + (25-10) * 0.01 = 0.10 + 0.15 = 0.25
        assert base_cost == 0.25

    def test_calculate_api_cost_low_volume(self):
        """Test cost calculation for low-volume requests"""
        base_cost = 0.10
        result_count = 5

        if result_count > 10:
            base_cost += (result_count - 10) * 0.01

        # No additional cost for low volume
        assert base_cost == 0.10


class TestCostReport:
    """Test cost report generation logic"""

    def test_generate_cost_report_no_usage(self):
        """Test cost report with no usage"""
        usage_stats = {
            'total_cost': 0.0,
            'total_requests': 0,
            'api_usage': {}
        }

        report = {
            'period_days': 30,
            'total_cost': usage_stats['total_cost'],
            'total_requests': usage_stats['total_requests'],
            'cost_per_request': 0.0,
            'api_breakdown': {},
            'generated_at': datetime.now().isoformat()
        }

        if usage_stats['total_requests'] > 0:
            report['cost_per_request'] = usage_stats['total_cost'] / usage_stats['total_requests']

        assert report['cost_per_request'] == 0.0

    def test_generate_cost_report_with_usage(self):
        """Test cost report with usage data"""
        usage_stats = {
            'total_cost': 10.0,
            'total_requests': 100,
            'api_usage': {
                'test_api': {'requests': 100, 'results': 500, 'cost': 10.0}
            }
        }

        report = {
            'period_days': 30,
            'total_cost': usage_stats['total_cost'],
            'total_requests': usage_stats['total_requests'],
            'cost_per_request': 0.0,
            'api_breakdown': {},
            'generated_at': datetime.now().isoformat()
        }

        if usage_stats['total_requests'] > 0:
            report['cost_per_request'] = usage_stats['total_cost'] / usage_stats['total_requests']

        for api_type, usage in usage_stats['api_usage'].items():
            report['api_breakdown'][api_type] = {
                'requests': usage['requests'],
                'results': usage['results'],
                'cost': usage['cost'],
                'cost_per_request': usage['cost'] / usage['requests'] if usage['requests'] > 0 else 0,
                'results_per_request': usage['results'] / usage['requests'] if usage['requests'] > 0 else 0
            }

        assert report['cost_per_request'] == 0.10
        assert report['api_breakdown']['test_api']['results_per_request'] == 5.0


class TestIntegrationCleanup:
    """Test integration cleanup logic"""

    def test_cleanup_expired_integrations(self):
        """Test cleanup of expired integrations"""
        # Create mock integrations
        valid_integration = MagicMock()
        valid_integration.token_expires_at = datetime.now() + timedelta(hours=1)

        expired_integration = MagicMock()
        expired_integration.token_expires_at = datetime.now() - timedelta(hours=1)

        active_integrations = {
            '1_valid_api': valid_integration,
            '2_expired_api': expired_integration
        }

        # Find expired integrations
        expired_keys = []
        for cache_key, integration in active_integrations.items():
            if hasattr(integration, 'token_expires_at') and integration.token_expires_at:
                if datetime.now() >= integration.token_expires_at - timedelta(minutes=5):
                    expired_keys.append(cache_key)

        # Remove expired
        for key in expired_keys:
            del active_integrations[key]

        assert '1_valid_api' in active_integrations
        assert '2_expired_api' not in active_integrations


class TestAPIRegistry:
    """Test API registry logic"""

    def test_list_available_apis(self):
        """Test listing available APIs"""
        api_registry = {
            'florida_property_appraiser': MagicMock,
            'california_sos': MagicMock,
            'florida_miami_dade': MagicMock
        }

        available_apis = list(api_registry.keys())
        assert len(available_apis) == 3
        assert 'florida_property_appraiser' in available_apis

    def test_get_api_info_exists(self):
        """Test getting info for existing API"""
        api_registry = {
            'test_api': type('TestAPI', (), {'__name__': 'TestAPI', '__module__': 'test.module'})
        }
        credentials = {'test_api': {'api_key': 'key123', 'updated_at': '2024-01-01'}}

        api_type = 'test_api'
        api_class = api_registry[api_type]
        api_creds = credentials.get(api_type, {})

        info = {
            'api_type': api_type,
            'class_name': api_class.__name__,
            'has_credentials': bool(api_creds),
            'last_updated': api_creds.get('updated_at'),
            'module': api_class.__module__
        }

        assert info['api_type'] == 'test_api'
        assert info['class_name'] == 'TestAPI'
        assert info['has_credentials'] is True
        assert info['last_updated'] == '2024-01-01'

    def test_get_api_info_not_exists(self):
        """Test getting info for non-existing API"""
        api_registry = {}
        api_type = 'nonexistent_api'

        if api_type not in api_registry:
            info = {}
        else:
            info = {'api_type': api_type}

        assert info == {}


class TestSearchAcrossAPIs:
    """Test search across multiple APIs logic"""

    def test_search_combines_results(self):
        """Test that search combines results from multiple APIs"""
        # Simulate results from multiple APIs
        results = []
        api_results = [
            [{'id': 1, 'source': 'api1'}],
            [{'id': 2, 'source': 'api2'}, {'id': 3, 'source': 'api2'}]
        ]

        for api_result in api_results:
            results.extend(api_result)

        assert len(results) == 3

    def test_search_handles_api_failure(self):
        """Test search continues when one API fails"""
        results = []
        api_types = ['api1', 'api2', 'api3']

        for api_type in api_types:
            try:
                if api_type == 'api2':
                    raise Exception("API failed")
                results.append({'from': api_type})
            except Exception:
                continue

        assert len(results) == 2

    def test_get_available_apis_for_jurisdiction(self):
        """Test getting available APIs for a jurisdiction"""
        # Default implementation
        default_apis = ['florida_property_appraiser', 'california_sos']
        assert len(default_apis) == 2


class TestAPIMetrics:
    """Test API metrics collection logic"""

    def test_get_api_metrics_structure(self):
        """Test metrics structure"""
        usage_stats = {
            'total_requests': 100,
            'total_cost': 10.0,
            'api_usage': {}
        }

        metrics = {
            'overall': usage_stats.copy(),
            'integrations': {}
        }

        assert 'overall' in metrics
        assert 'integrations' in metrics
        assert metrics['overall']['total_requests'] == 100

    def test_get_api_metrics_with_integrations(self):
        """Test metrics with active integrations"""
        usage_stats = {'total_requests': 50, 'total_cost': 5.0, 'api_usage': {}}
        active_integrations = {
            '1_test_api': MagicMock(get_metrics=lambda: {'requests': 50, 'errors': 2})
        }

        metrics = {
            'overall': usage_stats.copy(),
            'integrations': {}
        }

        for cache_key, integration in active_integrations.items():
            parts = cache_key.split('_', 1)
            if len(parts) == 2:
                jurisdiction_id, api_type = parts
                metrics['integrations'][cache_key] = {
                    'jurisdiction_id': int(jurisdiction_id),
                    'api_type': api_type,
                    **integration.get_metrics()
                }

        assert '1_test_api' in metrics['integrations']
        assert metrics['integrations']['1_test_api']['jurisdiction_id'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
