"""
Tests for BaseAPIIntegration classes.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


def create_test_integration_class():
    """Create a concrete test implementation of BaseAPIIntegration."""
    from datagod.scrapers.base_api_integration import BaseAPIIntegration

    class TestIntegration(BaseAPIIntegration):
        def authenticate(self):
            return True

        def search_property(self, **kwargs):
            return []

        def search_deed(self, **kwargs):
            return []

        def search_lien(self, **kwargs):
            return []

        def search_mortgage(self, **kwargs):
            return []

        def get_document(self, doc_id):
            return {}

        def search_records(self, **kwargs):
            return []

        def get_record_details(self, record_id):
            return {}

        def map_api_data_to_standard_format(self, data):
            return data

    return TestIntegration


class TestAPIIntegrationExceptions:
    """Tests for API integration exception classes."""

    def test_rate_limit_exceeded_exception(self):
        """Test RateLimitExceeded exception."""
        from datagod.scrapers.base_api_integration import RateLimitExceeded

        with pytest.raises(RateLimitExceeded):
            raise RateLimitExceeded("Rate limit exceeded")

    def test_api_authentication_error(self):
        """Test APIAuthenticationError exception."""
        from datagod.scrapers.base_api_integration import APIAuthenticationError

        with pytest.raises(APIAuthenticationError):
            raise APIAuthenticationError("Authentication failed")

    def test_api_data_error(self):
        """Test APIDataError exception."""
        from datagod.scrapers.base_api_integration import APIDataError

        with pytest.raises(APIDataError):
            raise APIDataError("Invalid data")


class TestAPIIntegrationMetrics:
    """Tests for APIIntegrationMetrics class."""

    def test_metrics_creation(self):
        """Test metrics can be created."""
        from datagod.scrapers.base_api_integration import APIIntegrationMetrics

        metrics = APIIntegrationMetrics()
        assert metrics is not None
        assert metrics.requests_total == 0
        assert metrics.requests_successful == 0
        assert metrics.requests_failed == 0

    def test_metrics_record_successful_request(self):
        """Test recording successful request."""
        from datagod.scrapers.base_api_integration import APIIntegrationMetrics

        metrics = APIIntegrationMetrics()
        metrics.record_request(success=True, response_time=0.5)

        assert metrics.requests_total == 1
        assert metrics.requests_successful == 1
        assert metrics.requests_failed == 0
        assert metrics.average_response_time == 0.5

    def test_metrics_record_failed_request(self):
        """Test recording failed request."""
        from datagod.scrapers.base_api_integration import APIIntegrationMetrics

        metrics = APIIntegrationMetrics()
        metrics.record_request(success=False, response_time=1.0, error_type="timeout")

        assert metrics.requests_total == 1
        assert metrics.requests_successful == 0
        assert metrics.requests_failed == 1
        assert "timeout" in metrics.errors_by_type
        assert metrics.errors_by_type["timeout"] == 1

    def test_metrics_record_multiple_requests(self):
        """Test recording multiple requests."""
        from datagod.scrapers.base_api_integration import APIIntegrationMetrics

        metrics = APIIntegrationMetrics()
        metrics.record_request(success=True, response_time=0.5)
        metrics.record_request(success=True, response_time=1.0)
        metrics.record_request(success=False, response_time=2.0, error_type="error")

        assert metrics.requests_total == 3
        assert metrics.requests_successful == 2
        assert metrics.requests_failed == 1
        assert metrics.average_response_time == (0.5 + 1.0 + 2.0) / 3

    def test_metrics_record_rate_limit_hit(self):
        """Test recording rate limit hit."""
        from datagod.scrapers.base_api_integration import APIIntegrationMetrics

        metrics = APIIntegrationMetrics()
        metrics.record_rate_limit_hit()
        metrics.record_rate_limit_hit()

        assert metrics.rate_limit_hits == 2

    def test_metrics_get_metrics(self):
        """Test getting metrics summary."""
        from datagod.scrapers.base_api_integration import APIIntegrationMetrics

        metrics = APIIntegrationMetrics()
        metrics.record_request(success=True, response_time=0.5)

        result = metrics.get_metrics()

        assert "requests_total" in result
        assert "requests_successful" in result
        assert "success_rate" in result
        assert "rate_limit_hits" in result
        assert "average_response_time" in result
        assert result["requests_total"] == 1
        assert result["success_rate"] == 100.0

    def test_metrics_get_metrics_zero_requests(self):
        """Test getting metrics with zero requests."""
        from datagod.scrapers.base_api_integration import APIIntegrationMetrics

        metrics = APIIntegrationMetrics()
        result = metrics.get_metrics()

        assert result["success_rate"] == 0

    def test_metrics_last_request_time(self):
        """Test last request time is recorded."""
        from datagod.scrapers.base_api_integration import APIIntegrationMetrics

        metrics = APIIntegrationMetrics()
        assert metrics.last_request_time is None

        metrics.record_request(success=True, response_time=0.1)
        assert metrics.last_request_time is not None


class TestBaseAPIIntegration:
    """Tests for BaseAPIIntegration class."""

    def test_base_api_integration_is_abstract(self):
        """Test BaseAPIIntegration is abstract."""
        from abc import ABC

        from datagod.scrapers.base_api_integration import BaseAPIIntegration

        assert issubclass(BaseAPIIntegration, ABC)

    def test_concrete_integration_creation(self):
        """Test concrete implementation can be created."""
        from datagod.scrapers.base_api_integration import BaseAPIIntegration

        class TestIntegration(BaseAPIIntegration):
            def authenticate(self):
                return True

            def search_property(self, **kwargs):
                return []

            def search_deed(self, **kwargs):
                return []

            def search_lien(self, **kwargs):
                return []

            def search_mortgage(self, **kwargs):
                return []

            def get_document(self, doc_id):
                return {}

            def search_records(self, **kwargs):
                return []

            def get_record_details(self, record_id):
                return {}

            def map_api_data_to_standard_format(self, data):
                return data

        config = {"base_url": "https://api.example.com", "api_key": "test_key"}

        integration = TestIntegration(jurisdiction_id=1, config=config)
        assert integration is not None
        assert integration.jurisdiction_id == 1
        assert integration.base_url == "https://api.example.com"

    def test_integration_default_config(self):
        """Test integration uses default config values."""
        TestIntegration = create_test_integration_class()

        config = {}
        integration = TestIntegration(jurisdiction_id=1, config=config)

        assert integration.requests_per_minute == 60
        assert integration.requests_per_hour == 1000
        assert integration.timeout == 30
        assert integration.retry_attempts == 3

    def test_integration_has_session(self):
        """Test integration creates HTTP session."""
        TestIntegration = create_test_integration_class()

        config = {"base_url": "https://api.example.com"}
        integration = TestIntegration(jurisdiction_id=1, config=config)

        assert integration.session is not None

    def test_integration_has_metrics(self):
        """Test integration has metrics tracking."""
        TestIntegration = create_test_integration_class()

        config = {"base_url": "https://api.example.com"}
        integration = TestIntegration(jurisdiction_id=1, config=config)

        assert integration.metrics is not None


class TestBaseAPIIntegrationRateLimiting:
    """Tests for rate limiting in BaseAPIIntegration."""

    def test_check_rate_limit_initial(self):
        """Test rate limit check with no requests."""
        TestIntegration = create_test_integration_class()

        config = {"requests_per_minute": 10, "requests_per_hour": 100}
        integration = TestIntegration(jurisdiction_id=1, config=config)

        assert integration._check_rate_limit() is True

    def test_check_rate_limit_per_minute_exceeded(self):
        """Test rate limit when per-minute limit is exceeded."""
        TestIntegration = create_test_integration_class()

        config = {"requests_per_minute": 5, "requests_per_hour": 100}
        integration = TestIntegration(jurisdiction_id=1, config=config)

        # Add timestamps to exceed per-minute limit
        now = datetime.now()
        integration.request_timestamps = [now - timedelta(seconds=i) for i in range(5)]

        assert integration._check_rate_limit() is False

    def test_check_rate_limit_per_hour_exceeded(self):
        """Test rate limit when per-hour limit is exceeded."""
        TestIntegration = create_test_integration_class()

        config = {"requests_per_minute": 100, "requests_per_hour": 5}
        integration = TestIntegration(jurisdiction_id=1, config=config)

        # Add timestamps to exceed per-hour limit
        now = datetime.now()
        integration.request_timestamps = [now - timedelta(minutes=i) for i in range(5)]

        assert integration._check_rate_limit() is False

    def test_record_request_timestamp(self):
        """Test recording request timestamp."""
        TestIntegration = create_test_integration_class()

        config = {}
        integration = TestIntegration(jurisdiction_id=1, config=config)

        assert len(integration.request_timestamps) == 0
        integration._record_request_timestamp()
        assert len(integration.request_timestamps) == 1

    def test_rate_limit_cleans_old_timestamps(self):
        """Test rate limit check cleans old timestamps."""
        TestIntegration = create_test_integration_class()

        config = {"requests_per_hour": 100}
        integration = TestIntegration(jurisdiction_id=1, config=config)

        # Add old timestamps (older than 1 hour)
        old_time = datetime.now() - timedelta(hours=2)
        integration.request_timestamps = [old_time for _ in range(50)]

        # Check rate limit (should clean old timestamps)
        result = integration._check_rate_limit()
        assert result is True
        assert len(integration.request_timestamps) == 0


class TestAPIKeyAuthentication:
    """Tests for APIKeyAuthentication class."""

    def test_api_key_authentication_import(self):
        """Test APIKeyAuthentication can be imported."""
        from datagod.scrapers.base_api_integration import APIKeyAuthentication

        assert APIKeyAuthentication is not None
