"""
Tests for datagod/scrapers/base_api_integration.py

Comprehensive tests for the Base API Integration Framework.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import time
import requests


class TestExceptionClasses:
    """Tests for exception classes"""

    def test_rate_limit_exceeded_exists(self):
        """Test that RateLimitExceeded exception exists"""
        from datagod.scrapers.base_api_integration import RateLimitExceeded
        assert RateLimitExceeded is not None
        assert issubclass(RateLimitExceeded, Exception)

    def test_api_authentication_error_exists(self):
        """Test that APIAuthenticationError exception exists"""
        from datagod.scrapers.base_api_integration import APIAuthenticationError
        assert APIAuthenticationError is not None
        assert issubclass(APIAuthenticationError, Exception)

    def test_api_data_error_exists(self):
        """Test that APIDataError exception exists"""
        from datagod.scrapers.base_api_integration import APIDataError
        assert APIDataError is not None
        assert issubclass(APIDataError, Exception)

    def test_rate_limit_exceeded_message(self):
        """Test RateLimitExceeded with message"""
        from datagod.scrapers.base_api_integration import RateLimitExceeded

        with pytest.raises(RateLimitExceeded) as excinfo:
            raise RateLimitExceeded("Rate limit hit")
        assert "Rate limit hit" in str(excinfo.value)


class TestAPIIntegrationMetrics:
    """Tests for APIIntegrationMetrics class"""

    def test_metrics_class_exists(self):
        """Test that APIIntegrationMetrics class exists"""
        from datagod.scrapers.base_api_integration import APIIntegrationMetrics
        assert APIIntegrationMetrics is not None

    def test_metrics_init(self):
        """Test APIIntegrationMetrics initialization"""
        from datagod.scrapers.base_api_integration import APIIntegrationMetrics

        metrics = APIIntegrationMetrics()
        assert metrics.requests_total == 0
        assert metrics.requests_successful == 0
        assert metrics.requests_failed == 0
        assert metrics.rate_limit_hits == 0
        assert metrics.average_response_time == 0.0

    def test_record_successful_request(self):
        """Test recording a successful request"""
        from datagod.scrapers.base_api_integration import APIIntegrationMetrics

        metrics = APIIntegrationMetrics()
        metrics.record_request(success=True, response_time=0.5)

        assert metrics.requests_total == 1
        assert metrics.requests_successful == 1
        assert metrics.requests_failed == 0
        assert metrics.average_response_time == 0.5

    def test_record_failed_request(self):
        """Test recording a failed request"""
        from datagod.scrapers.base_api_integration import APIIntegrationMetrics

        metrics = APIIntegrationMetrics()
        metrics.record_request(success=False, response_time=0.3, error_type='timeout')

        assert metrics.requests_total == 1
        assert metrics.requests_successful == 0
        assert metrics.requests_failed == 1
        assert 'timeout' in metrics.errors_by_type

    def test_record_rate_limit_hit(self):
        """Test recording rate limit hit"""
        from datagod.scrapers.base_api_integration import APIIntegrationMetrics

        metrics = APIIntegrationMetrics()
        metrics.record_rate_limit_hit()

        assert metrics.rate_limit_hits == 1

    def test_get_metrics(self):
        """Test getting metrics dictionary"""
        from datagod.scrapers.base_api_integration import APIIntegrationMetrics

        metrics = APIIntegrationMetrics()
        metrics.record_request(success=True, response_time=0.5)
        metrics.record_request(success=False, response_time=0.3, error_type='error')

        result = metrics.get_metrics()

        assert 'requests_total' in result
        assert 'requests_successful' in result
        assert 'requests_failed' in result
        assert 'success_rate' in result
        assert 'average_response_time' in result
        assert result['requests_total'] == 2
        assert result['success_rate'] == 50.0

    def test_average_response_time_calculation(self):
        """Test average response time is calculated correctly"""
        from datagod.scrapers.base_api_integration import APIIntegrationMetrics

        metrics = APIIntegrationMetrics()
        metrics.record_request(success=True, response_time=1.0)
        metrics.record_request(success=True, response_time=2.0)
        metrics.record_request(success=True, response_time=3.0)

        assert metrics.average_response_time == 2.0


class TestBaseAPIIntegration:
    """Tests for BaseAPIIntegration abstract base class"""

    def test_base_api_integration_exists(self):
        """Test that BaseAPIIntegration class exists"""
        from datagod.scrapers.base_api_integration import BaseAPIIntegration
        assert BaseAPIIntegration is not None

    def test_base_api_integration_is_abstract(self):
        """Test that BaseAPIIntegration is abstract"""
        from datagod.scrapers.base_api_integration import BaseAPIIntegration
        from abc import ABC
        assert issubclass(BaseAPIIntegration, ABC)

    def test_has_abstract_methods(self):
        """Test that required abstract methods exist"""
        from datagod.scrapers.base_api_integration import BaseAPIIntegration

        assert hasattr(BaseAPIIntegration, 'authenticate')
        assert hasattr(BaseAPIIntegration, 'search_records')
        assert hasattr(BaseAPIIntegration, 'get_record_details')
        assert hasattr(BaseAPIIntegration, 'map_api_data_to_standard_format')


class TestConcreteAPIIntegration:
    """Tests for BaseAPIIntegration with concrete implementation"""

    @pytest.fixture
    def concrete_api(self):
        """Create a concrete implementation of BaseAPIIntegration"""
        from datagod.scrapers.base_api_integration import BaseAPIIntegration

        class ConcreteAPI(BaseAPIIntegration):
            def authenticate(self):
                return True

            def search_records(self, query, **kwargs):
                return []

            def get_record_details(self, record_id):
                return {}

            def map_api_data_to_standard_format(self, api_data):
                return api_data

        return ConcreteAPI

    def test_init_sets_jurisdiction_id(self, concrete_api):
        """Test that init sets jurisdiction_id"""
        api = concrete_api(jurisdiction_id=123, config={})
        assert api.jurisdiction_id == 123

    def test_init_sets_config(self, concrete_api):
        """Test that init sets config"""
        config = {'key': 'value'}
        api = concrete_api(jurisdiction_id=1, config=config)
        assert api.config == config

    def test_init_creates_metrics(self, concrete_api):
        """Test that init creates metrics object"""
        from datagod.scrapers.base_api_integration import APIIntegrationMetrics

        api = concrete_api(jurisdiction_id=1, config={})
        assert isinstance(api.metrics, APIIntegrationMetrics)

    def test_init_sets_rate_limits(self, concrete_api):
        """Test that init sets rate limits from config"""
        config = {'requests_per_minute': 30, 'requests_per_hour': 500}
        api = concrete_api(jurisdiction_id=1, config=config)

        assert api.requests_per_minute == 30
        assert api.requests_per_hour == 500

    def test_init_sets_default_rate_limits(self, concrete_api):
        """Test that init uses default rate limits"""
        api = concrete_api(jurisdiction_id=1, config={})

        assert api.requests_per_minute == 60
        assert api.requests_per_hour == 1000

    def test_init_sets_timeout(self, concrete_api):
        """Test that init sets timeout"""
        config = {'timeout': 60}
        api = concrete_api(jurisdiction_id=1, config=config)

        assert api.timeout == 60

    def test_init_creates_session(self, concrete_api):
        """Test that init creates HTTP session"""
        api = concrete_api(jurisdiction_id=1, config={})
        assert api.session is not None
        assert isinstance(api.session, requests.Session)


class TestRateLimiting:
    """Tests for rate limiting functionality"""

    @pytest.fixture
    def api(self):
        """Create a concrete API for testing"""
        from datagod.scrapers.base_api_integration import BaseAPIIntegration

        class ConcreteAPI(BaseAPIIntegration):
            def authenticate(self):
                return True

            def search_records(self, query, **kwargs):
                return []

            def get_record_details(self, record_id):
                return {}

            def map_api_data_to_standard_format(self, api_data):
                return api_data

        return ConcreteAPI(
            jurisdiction_id=1,
            config={'requests_per_minute': 5, 'requests_per_hour': 100}
        )

    def test_check_rate_limit_returns_true_when_within_limits(self, api):
        """Test that _check_rate_limit returns True when within limits"""
        assert api._check_rate_limit() is True

    def test_check_rate_limit_returns_false_when_exceeded(self, api):
        """Test that _check_rate_limit returns False when exceeded"""
        # Add timestamps for 5 requests in the last minute
        now = datetime.now()
        api.request_timestamps = [now - timedelta(seconds=i) for i in range(5)]

        assert api._check_rate_limit() is False

    def test_record_request_timestamp(self, api):
        """Test that _record_request_timestamp adds timestamp"""
        assert len(api.request_timestamps) == 0

        api._record_request_timestamp()

        assert len(api.request_timestamps) == 1

    def test_record_request_timestamp_limits_list_size(self, api):
        """Test that timestamps list is limited to 1000"""
        # Add 1001 timestamps
        now = datetime.now()
        api.request_timestamps = [now for _ in range(1001)]

        api._record_request_timestamp()

        assert len(api.request_timestamps) <= 1000


class TestAuthentication:
    """Tests for authentication functionality"""

    @pytest.fixture
    def api_with_auth(self):
        """Create API with authentication configured"""
        from datagod.scrapers.base_api_integration import BaseAPIIntegration

        class ConcreteAPI(BaseAPIIntegration):
            def authenticate(self):
                self.access_token = 'test_token'
                self.token_expires_at = datetime.now() + timedelta(hours=1)
                return True

            def search_records(self, query, **kwargs):
                return []

            def get_record_details(self, record_id):
                return {}

            def map_api_data_to_standard_format(self, api_data):
                return api_data

        return ConcreteAPI(
            jurisdiction_id=1,
            config={'api_key': 'test_key', 'api_secret': 'test_secret'}
        )

    def test_ensure_authenticated_calls_authenticate_when_no_token(self, api_with_auth):
        """Test that _ensure_authenticated calls authenticate when no token"""
        api_with_auth.access_token = None
        result = api_with_auth._ensure_authenticated()
        assert result is True
        assert api_with_auth.access_token == 'test_token'

    def test_ensure_authenticated_returns_true_when_token_valid(self, api_with_auth):
        """Test that _ensure_authenticated returns True when token is valid"""
        api_with_auth.access_token = 'existing_token'
        api_with_auth.token_expires_at = datetime.now() + timedelta(hours=1)

        result = api_with_auth._ensure_authenticated()
        assert result is True

    def test_get_auth_headers_includes_api_key(self, api_with_auth):
        """Test that _get_auth_headers includes API key"""
        headers = api_with_auth._get_auth_headers('GET', '/test', {})
        assert 'X-API-Key' in headers
        assert headers['X-API-Key'] == 'test_key'

    def test_get_auth_headers_includes_bearer_token(self, api_with_auth):
        """Test that _get_auth_headers includes Bearer token"""
        api_with_auth.access_token = 'test_token'
        headers = api_with_auth._get_auth_headers('GET', '/test', {})

        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Bearer test_token'


class TestValidateResponse:
    """Tests for response validation"""

    @pytest.fixture
    def api(self):
        """Create a concrete API for testing"""
        from datagod.scrapers.base_api_integration import BaseAPIIntegration

        class ConcreteAPI(BaseAPIIntegration):
            def authenticate(self):
                return True

            def search_records(self, query, **kwargs):
                return []

            def get_record_details(self, record_id):
                return {}

            def map_api_data_to_standard_format(self, api_data):
                return api_data

        return ConcreteAPI(jurisdiction_id=1, config={})

    def test_validate_response_returns_json_on_success(self, api):
        """Test that validate_response returns JSON on success"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}

        result = api.validate_response(mock_response)
        assert result == {'data': 'test'}

    def test_validate_response_raises_on_error_status(self, api):
        """Test that validate_response raises on error status"""
        from datagod.scrapers.base_api_integration import APIDataError

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'

        with pytest.raises(APIDataError):
            api.validate_response(mock_response)

    def test_validate_response_raises_on_invalid_json(self, api):
        """Test that validate_response raises on invalid JSON"""
        from datagod.scrapers.base_api_integration import APIDataError
        import json

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError('error', '', 0)
        mock_response.text = 'not json'

        with pytest.raises(APIDataError):
            api.validate_response(mock_response)


class TestGetMetrics:
    """Tests for get_metrics method"""

    @pytest.fixture
    def api(self):
        """Create a concrete API for testing"""
        from datagod.scrapers.base_api_integration import BaseAPIIntegration

        class ConcreteAPI(BaseAPIIntegration):
            def authenticate(self):
                return True

            def search_records(self, query, **kwargs):
                return []

            def get_record_details(self, record_id):
                return {}

            def map_api_data_to_standard_format(self, api_data):
                return api_data

        return ConcreteAPI(jurisdiction_id=123, config={'base_url': 'https://test.com'})

    def test_get_metrics_includes_jurisdiction_id(self, api):
        """Test that get_metrics includes jurisdiction_id"""
        metrics = api.get_metrics()
        assert 'jurisdiction_id' in metrics
        assert metrics['jurisdiction_id'] == 123

    def test_get_metrics_includes_api_name(self, api):
        """Test that get_metrics includes api_name"""
        metrics = api.get_metrics()
        assert 'api_name' in metrics
        assert metrics['api_name'] == 'ConcreteAPI'

    def test_get_metrics_includes_config(self, api):
        """Test that get_metrics includes config"""
        metrics = api.get_metrics()
        assert 'config' in metrics
        assert 'base_url' in metrics['config']


class TestAPIKeyAuthentication:
    """Tests for APIKeyAuthentication mixin"""

    def test_api_key_authentication_exists(self):
        """Test that APIKeyAuthentication class exists"""
        from datagod.scrapers.base_api_integration import APIKeyAuthentication
        assert APIKeyAuthentication is not None

    def test_authenticate_returns_false_without_key(self):
        """Test that authenticate returns False without API key"""
        from datagod.scrapers.base_api_integration import APIKeyAuthentication

        mixin = APIKeyAuthentication()
        mixin.api_key = None

        result = mixin.authenticate()
        assert result is False

    def test_authenticate_returns_true_with_key(self):
        """Test that authenticate returns True with API key"""
        from datagod.scrapers.base_api_integration import APIKeyAuthentication

        mixin = APIKeyAuthentication()
        mixin.api_key = 'test_key'

        result = mixin.authenticate()
        assert result is True


class TestOAuth2Authentication:
    """Tests for OAuth2Authentication mixin"""

    def test_oauth2_authentication_exists(self):
        """Test that OAuth2Authentication class exists"""
        from datagod.scrapers.base_api_integration import OAuth2Authentication
        assert OAuth2Authentication is not None

    def test_oauth2_init_sets_credentials(self):
        """Test that OAuth2 init sets credentials from config"""
        from datagod.scrapers.base_api_integration import OAuth2Authentication, BaseAPIIntegration

        class TestOAuth2(OAuth2Authentication, BaseAPIIntegration):
            def search_records(self, query, **kwargs):
                return []

            def get_record_details(self, record_id):
                return {}

            def map_api_data_to_standard_format(self, api_data):
                return api_data

        config = {
            'token_url': 'https://auth.test.com/token',
            'client_id': 'test_client',
            'client_secret': 'test_secret',
            'scope': 'read'
        }

        api = TestOAuth2(jurisdiction_id=1, config=config)

        assert api.token_url == 'https://auth.test.com/token'
        assert api.client_id == 'test_client'
        assert api.client_secret == 'test_secret'
        assert api.scope == 'read'


class TestHMACAuthentication:
    """Tests for HMACAuthentication mixin"""

    def test_hmac_authentication_exists(self):
        """Test that HMACAuthentication class exists"""
        from datagod.scrapers.base_api_integration import HMACAuthentication
        assert HMACAuthentication is not None

    def test_hmac_get_auth_headers_adds_signature(self):
        """Test that HMAC auth adds signature headers"""
        from datagod.scrapers.base_api_integration import HMACAuthentication, BaseAPIIntegration

        class TestHMAC(HMACAuthentication, BaseAPIIntegration):
            def authenticate(self):
                return True

            def search_records(self, query, **kwargs):
                return []

            def get_record_details(self, record_id):
                return {}

            def map_api_data_to_standard_format(self, api_data):
                return api_data

        api = TestHMAC(
            jurisdiction_id=1,
            config={'api_key': 'test_key', 'api_secret': 'test_secret'}
        )

        headers = api._get_auth_headers('GET', '/test', {})

        assert 'X-API-Key' in headers
        assert 'X-Timestamp' in headers
        assert 'X-Signature' in headers
