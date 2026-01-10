"""
Tests for Application Performance Monitoring middleware.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import time


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    def test_singleton_pattern(self):
        """Test that MetricsCollector is a singleton."""
        from api.src.middleware.monitoring import MetricsCollector

        collector1 = MetricsCollector()
        collector2 = MetricsCollector()

        assert collector1 is collector2

    def test_record_request(self):
        """Test recording request metrics."""
        from api.src.middleware.monitoring import MetricsCollector

        collector = MetricsCollector()
        collector.reset()

        collector.record_request(
            endpoint='/api/test',
            method='GET',
            status_code=200,
            latency=0.1,
            user_id='user123'
        )

        metrics = collector.get_metrics()

        assert metrics['total_requests'] >= 1
        assert 'GET:/api/test' in metrics['requests_by_endpoint']

    def test_record_error(self):
        """Test recording error metrics."""
        from api.src.middleware.monitoring import MetricsCollector

        collector = MetricsCollector()
        collector.reset()

        collector.record_request(
            endpoint='/api/error',
            method='POST',
            status_code=500,
            latency=0.05,
        )

        metrics = collector.get_metrics()

        assert metrics['total_errors'] >= 1
        assert 'POST:/api/error' in metrics['errors_by_endpoint']

    def test_connection_tracking(self):
        """Test active connection tracking."""
        from api.src.middleware.monitoring import MetricsCollector

        collector = MetricsCollector()
        collector.reset()

        initial = collector.active_connections

        collector.increment_connections()
        assert collector.active_connections == initial + 1

        collector.increment_connections()
        assert collector.active_connections == initial + 2

        collector.decrement_connections()
        assert collector.active_connections == initial + 1

        collector.decrement_connections()
        assert collector.active_connections == initial

    def test_latency_statistics(self):
        """Test latency statistics calculation."""
        from api.src.middleware.monitoring import MetricsCollector

        collector = MetricsCollector()
        collector.reset()

        # Record multiple requests with known latencies
        for latency in [0.1, 0.2, 0.3, 0.4, 0.5]:
            collector.record_request(
                endpoint='/api/stats',
                method='GET',
                status_code=200,
                latency=latency,
            )

        metrics = collector.get_metrics()
        stats = metrics['latency_stats'].get('GET:/api/stats', {})

        assert stats.get('count', 0) == 5
        assert stats.get('min', 0) == 0.1
        assert stats.get('max', 0) == 0.5
        assert 0.25 <= stats.get('avg', 0) <= 0.35  # Approximately 0.3

    def test_reset_metrics(self):
        """Test resetting all metrics."""
        from api.src.middleware.monitoring import MetricsCollector

        collector = MetricsCollector()

        collector.record_request(
            endpoint='/api/test',
            method='GET',
            status_code=200,
            latency=0.1,
        )

        collector.reset()

        metrics = collector.get_metrics()

        assert metrics['total_requests'] == 0
        assert metrics['total_errors'] == 0

    def test_uptime_tracking(self):
        """Test uptime calculation."""
        from api.src.middleware.monitoring import MetricsCollector

        collector = MetricsCollector()
        collector.reset()

        time.sleep(0.1)

        metrics = collector.get_metrics()

        assert metrics['uptime_seconds'] >= 0.1

    def test_top_users(self):
        """Test top users tracking."""
        from api.src.middleware.monitoring import MetricsCollector

        collector = MetricsCollector()
        collector.reset()

        # User1 makes 5 requests
        for _ in range(5):
            collector.record_request(
                endpoint='/api/test',
                method='GET',
                status_code=200,
                latency=0.1,
                user_id='user1'
            )

        # User2 makes 3 requests
        for _ in range(3):
            collector.record_request(
                endpoint='/api/test',
                method='GET',
                status_code=200,
                latency=0.1,
                user_id='user2'
            )

        metrics = collector.get_metrics()
        top_users = metrics['top_users']

        assert 'user1' in top_users
        assert 'user2' in top_users
        assert top_users['user1'] >= top_users['user2']


class TestHealthChecker:
    """Tests for HealthChecker class."""

    def test_liveness_check(self):
        """Test liveness check always returns ok."""
        from api.src.middleware.monitoring import HealthChecker

        checker = HealthChecker()
        result = checker.get_liveness()

        assert result['status'] == 'ok'
        assert 'timestamp' in result

    def test_readiness_check_structure(self):
        """Test readiness check returns proper structure."""
        from api.src.middleware.monitoring import HealthChecker

        checker = HealthChecker()
        result = checker.get_readiness()

        assert 'status' in result
        assert 'timestamp' in result
        assert 'checks' in result
        assert 'ready' in result

    @patch('api.src.middleware.monitoring.HealthChecker.check_database')
    @patch('api.src.middleware.monitoring.HealthChecker.check_redis')
    def test_readiness_all_healthy(self, mock_redis, mock_db):
        """Test readiness when all checks pass."""
        mock_db.return_value = True
        mock_redis.return_value = True

        from api.src.middleware.monitoring import HealthChecker

        checker = HealthChecker()
        result = checker.get_readiness()

        assert result['status'] == 'ok'
        assert result['ready'] is True

    @patch('api.src.middleware.monitoring.HealthChecker.check_database')
    @patch('api.src.middleware.monitoring.HealthChecker.check_redis')
    def test_readiness_database_failed(self, mock_redis, mock_db):
        """Test readiness when database check fails."""
        mock_db.return_value = False
        mock_redis.return_value = True

        from api.src.middleware.monitoring import HealthChecker

        checker = HealthChecker()
        result = checker.get_readiness()

        assert result['status'] == 'degraded'
        assert result['ready'] is False
        assert result['checks']['database'] == 'failed'


class TestTimedDecorators:
    """Tests for timing decorators."""

    def test_timed_decorator(self):
        """Test timed decorator measures execution time."""
        from api.src.middleware.monitoring import timed

        @timed
        def slow_function():
            time.sleep(0.1)
            return 'done'

        result = slow_function()

        assert result == 'done'

    def test_timed_decorator_preserves_return(self):
        """Test timed decorator preserves return value."""
        from api.src.middleware.monitoring import timed

        @timed
        def calculate():
            return 42

        result = calculate()

        assert result == 42


class TestGlobalInstances:
    """Tests for global singleton instances."""

    def test_metrics_collector_instance(self):
        """Test global metrics collector is accessible."""
        from api.src.middleware.monitoring import metrics_collector

        assert metrics_collector is not None
        assert hasattr(metrics_collector, 'record_request')
        assert hasattr(metrics_collector, 'get_metrics')

    def test_health_checker_instance(self):
        """Test global health checker is accessible."""
        from api.src.middleware.monitoring import health_checker

        assert health_checker is not None
        assert hasattr(health_checker, 'get_liveness')
        assert hasattr(health_checker, 'get_readiness')


class TestStatusCodeTracking:
    """Tests for HTTP status code tracking."""

    def test_status_code_distribution(self):
        """Test status code distribution tracking."""
        from api.src.middleware.monitoring import MetricsCollector

        collector = MetricsCollector()
        collector.reset()

        # Record various status codes
        collector.record_request('/api/test', 'GET', 200, 0.1)
        collector.record_request('/api/test', 'GET', 200, 0.1)
        collector.record_request('/api/test', 'GET', 404, 0.1)
        collector.record_request('/api/test', 'POST', 500, 0.1)

        metrics = collector.get_metrics()
        status_codes = metrics['status_codes']

        assert status_codes.get(200, 0) == 2
        assert status_codes.get(404, 0) == 1
        assert status_codes.get(500, 0) == 1

    def test_error_rate_calculation(self):
        """Test error rate percentage calculation."""
        from api.src.middleware.monitoring import MetricsCollector

        collector = MetricsCollector()
        collector.reset()

        # 8 successful, 2 errors = 20% error rate
        for _ in range(8):
            collector.record_request('/api/test', 'GET', 200, 0.1)
        for _ in range(2):
            collector.record_request('/api/test', 'GET', 500, 0.1)

        metrics = collector.get_metrics()

        assert metrics['error_rate_percent'] == 20.0
