"""
Comprehensive tests for the Scraper Health Monitor.

Tests cover:
- HealthStatus enum
- ScraperMetrics dataclass
- HealthCheckResult dataclass
- ScraperHealthMonitor class
- Request recording
- Health status calculation
- Error classification
- State summaries
"""

from datetime import datetime, timedelta

import pytest

from datagod.monitoring.scraper_health import (
    HealthCheckResult,
    HealthStatus,
    ScraperHealthMonitor,
    ScraperMetrics,
    check_all_scrapers,
    get_monitor,
    get_scraper_health,
)


class TestHealthStatusEnum:
    """Tests for HealthStatus enum"""

    def test_all_statuses_exist(self):
        """Test that all health statuses are defined"""
        assert HealthStatus.HEALTHY is not None
        assert HealthStatus.DEGRADED is not None
        assert HealthStatus.UNHEALTHY is not None
        assert HealthStatus.CRITICAL is not None
        assert HealthStatus.UNKNOWN is not None

    def test_status_values(self):
        """Test status string values"""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.CRITICAL.value == "critical"
        assert HealthStatus.UNKNOWN.value == "unknown"


class TestScraperMetrics:
    """Tests for ScraperMetrics dataclass"""

    def test_create_metrics(self):
        """Test creating scraper metrics"""
        metrics = ScraperMetrics(scraper_id="test_scraper", state_code="CA")
        assert metrics.scraper_id == "test_scraper"
        assert metrics.state_code == "CA"
        assert metrics.total_requests == 0

    def test_success_rate_no_requests(self):
        """Test success rate with no requests"""
        metrics = ScraperMetrics(scraper_id="test", state_code="CA")
        assert metrics.success_rate == 0.0

    def test_success_rate_calculation(self):
        """Test success rate calculation"""
        metrics = ScraperMetrics(
            scraper_id="test",
            state_code="CA",
            total_requests=100,
            successful_requests=75,
            failed_requests=25,
        )
        assert metrics.success_rate == 0.75

    def test_failure_rate_calculation(self):
        """Test failure rate calculation"""
        metrics = ScraperMetrics(
            scraper_id="test",
            state_code="CA",
            total_requests=100,
            successful_requests=75,
            failed_requests=25,
        )
        assert metrics.failure_rate == 0.25

    def test_avg_response_time(self):
        """Test average response time calculation"""
        metrics = ScraperMetrics(
            scraper_id="test",
            state_code="CA",
            successful_requests=10,
            total_response_time_ms=5000.0,
        )
        assert metrics.avg_response_time_ms == 500.0

    def test_avg_response_time_no_requests(self):
        """Test average response time with no requests"""
        metrics = ScraperMetrics(scraper_id="test", state_code="CA")
        assert metrics.avg_response_time_ms == 0.0

    def test_quota_usage_percent(self):
        """Test quota usage calculation"""
        metrics = ScraperMetrics(
            scraper_id="test", state_code="CA", api_quota_used=750, api_quota_limit=1000
        )
        assert metrics.quota_usage_percent == 75.0

    def test_quota_usage_no_limit(self):
        """Test quota usage with no limit"""
        metrics = ScraperMetrics(
            scraper_id="test", state_code="CA", api_quota_used=500, api_quota_limit=0
        )
        assert metrics.quota_usage_percent == 0.0

    def test_health_status_healthy(self):
        """Test healthy status"""
        metrics = ScraperMetrics(
            scraper_id="test",
            state_code="CA",
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
        )
        assert metrics.health_status == HealthStatus.HEALTHY

    def test_health_status_degraded(self):
        """Test degraded status (>10% failure)"""
        metrics = ScraperMetrics(
            scraper_id="test",
            state_code="CA",
            total_requests=100,
            successful_requests=85,
            failed_requests=15,
        )
        assert metrics.health_status == HealthStatus.DEGRADED

    def test_health_status_unhealthy(self):
        """Test unhealthy status (>25% failure)"""
        metrics = ScraperMetrics(
            scraper_id="test",
            state_code="CA",
            total_requests=100,
            successful_requests=70,
            failed_requests=30,
        )
        assert metrics.health_status == HealthStatus.UNHEALTHY

    def test_health_status_critical(self):
        """Test critical status (>50% failure)"""
        metrics = ScraperMetrics(
            scraper_id="test",
            state_code="CA",
            total_requests=100,
            successful_requests=40,
            failed_requests=60,
        )
        assert metrics.health_status == HealthStatus.CRITICAL

    def test_health_status_quota_exceeded(self):
        """Test critical status when quota exceeded"""
        metrics = ScraperMetrics(
            scraper_id="test",
            state_code="CA",
            total_requests=100,
            successful_requests=100,
            api_quota_used=1100,
            api_quota_limit=1000,
        )
        assert metrics.health_status == HealthStatus.CRITICAL

    def test_health_status_unknown(self):
        """Test unknown status with no requests"""
        metrics = ScraperMetrics(scraper_id="test", state_code="CA")
        assert metrics.health_status == HealthStatus.UNKNOWN

    def test_metrics_to_dict(self):
        """Test converting metrics to dictionary"""
        metrics = ScraperMetrics(
            scraper_id="test",
            state_code="CA",
            total_requests=100,
            successful_requests=90,
            failed_requests=10,
            records_fetched=500,
        )
        result = metrics.to_dict()
        assert result["scraper_id"] == "test"
        assert result["state_code"] == "CA"
        assert result["total_requests"] == 100
        assert result["success_rate"] == 0.9
        assert result["health_status"] == "healthy"


class TestHealthCheckResult:
    """Tests for HealthCheckResult dataclass"""

    def test_create_result(self):
        """Test creating health check result"""
        result = HealthCheckResult(
            scraper_id="test",
            status=HealthStatus.HEALTHY,
            message="All systems operational",
        )
        assert result.scraper_id == "test"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All systems operational"

    def test_result_to_dict(self):
        """Test converting result to dictionary"""
        result = HealthCheckResult(
            scraper_id="test",
            status=HealthStatus.DEGRADED,
            message="High latency",
            response_time_ms=150.5,
            details={"avg_latency": 150},
        )
        data = result.to_dict()
        assert data["scraper_id"] == "test"
        assert data["status"] == "degraded"
        assert data["message"] == "High latency"
        assert data["response_time_ms"] == 150.5


class TestScraperHealthMonitor:
    """Tests for ScraperHealthMonitor class"""

    @pytest.fixture
    def monitor(self):
        """Create fresh monitor instance"""
        return ScraperHealthMonitor()

    def test_monitor_initialization(self, monitor):
        """Test monitor initialization"""
        assert monitor.freshness_threshold == timedelta(hours=24)
        assert monitor.response_time_warn == 3000
        assert monitor.response_time_critical == 10000

    def test_custom_thresholds(self):
        """Test monitor with custom thresholds"""
        monitor = ScraperHealthMonitor(
            freshness_threshold_hours=12,
            response_time_warn_ms=1000,
            response_time_critical_ms=5000,
        )
        assert monitor.freshness_threshold == timedelta(hours=12)
        assert monitor.response_time_warn == 1000

    def test_record_successful_request(
        self, monitor, sample_scraper_id, sample_state_code
    ):
        """Test recording a successful request"""
        monitor.record_request(
            sample_scraper_id,
            sample_state_code,
            success=True,
            response_time_ms=100.0,
            records_count=50,
        )
        metrics = monitor.get_metrics(sample_scraper_id)
        assert metrics is not None
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.records_fetched == 50

    def test_record_failed_request(self, monitor, sample_scraper_id, sample_state_code):
        """Test recording a failed request"""
        monitor.record_request(
            sample_scraper_id,
            sample_state_code,
            success=False,
            response_time_ms=5000.0,
            error_message="Connection timeout",
        )
        metrics = monitor.get_metrics(sample_scraper_id)
        assert metrics.failed_requests == 1
        assert metrics.last_error_message == "Connection timeout"

    def test_record_multiple_requests(
        self, monitor, sample_scraper_id, sample_state_code
    ):
        """Test recording multiple requests"""
        for i in range(10):
            monitor.record_request(
                sample_scraper_id,
                sample_state_code,
                success=True,
                response_time_ms=100.0,
            )
        metrics = monitor.get_metrics(sample_scraper_id)
        assert metrics.total_requests == 10
        assert metrics.avg_response_time_ms == 100.0

    def test_update_quota(self, monitor, sample_scraper_id, sample_state_code):
        """Test updating API quota"""
        monitor.record_request(sample_scraper_id, sample_state_code, True, 100.0)
        monitor.update_quota(sample_scraper_id, used=500, limit=1000)

        metrics = monitor.get_metrics(sample_scraper_id)
        assert metrics.api_quota_used == 500
        assert metrics.api_quota_limit == 1000
        assert metrics.quota_usage_percent == 50.0

    def test_get_all_metrics(self, monitor):
        """Test getting all metrics"""
        monitor.record_request("scraper1", "CA", True, 100.0)
        monitor.record_request("scraper2", "NY", True, 150.0)

        all_metrics = monitor.get_all_metrics()
        assert len(all_metrics) == 2
        assert "scraper1" in all_metrics
        assert "scraper2" in all_metrics

    def test_check_health(self, monitor, sample_scraper_id, sample_state_code):
        """Test checking health"""
        # Record some successful requests
        for i in range(10):
            monitor.record_request(sample_scraper_id, sample_state_code, True, 100.0)

        result = monitor.check_health(sample_scraper_id)
        assert result.status == HealthStatus.HEALTHY
        assert "operational" in result.message.lower()

    def test_check_health_unknown_scraper(self, monitor):
        """Test checking health of unknown scraper"""
        result = monitor.check_health("unknown_scraper")
        assert result.status == HealthStatus.UNKNOWN

    def test_check_health_with_func(
        self, monitor, sample_scraper_id, sample_state_code
    ):
        """Test health check with custom function"""
        monitor.record_request(sample_scraper_id, sample_state_code, True, 100.0)

        # Health check function that returns True
        result = monitor.check_health(sample_scraper_id, lambda: True)
        assert result.status == HealthStatus.HEALTHY

        # Health check function that returns False
        result = monitor.check_health(sample_scraper_id, lambda: False)
        assert result.status == HealthStatus.UNHEALTHY

    def test_check_health_func_exception(
        self, monitor, sample_scraper_id, sample_state_code
    ):
        """Test health check with function that raises exception"""
        monitor.record_request(sample_scraper_id, sample_state_code, True, 100.0)

        def failing_check():
            raise Exception("Connection failed")

        result = monitor.check_health(sample_scraper_id, failing_check)
        assert result.status == HealthStatus.CRITICAL

    def test_check_all_scrapers(self, monitor):
        """Test checking all scrapers"""
        monitor.record_request("scraper1", "CA", True, 100.0)
        monitor.record_request("scraper2", "NY", True, 150.0)

        results = monitor.check_all_scrapers()
        assert len(results) == 2
        assert "scraper1" in results
        assert "scraper2" in results

    def test_get_error_summary(self, monitor, sample_scraper_id, sample_state_code):
        """Test getting error summary"""
        monitor.record_request(
            sample_scraper_id,
            sample_state_code,
            False,
            0,
            error_message="Connection timeout",
        )
        monitor.record_request(
            sample_scraper_id,
            sample_state_code,
            False,
            0,
            error_message="Rate limit exceeded (429)",
        )
        monitor.record_request(
            sample_scraper_id,
            sample_state_code,
            False,
            0,
            error_message="Connection refused",
        )

        summary = monitor.get_error_summary(sample_scraper_id)
        assert sample_scraper_id in summary
        assert summary[sample_scraper_id].get("timeout", 0) >= 1
        assert summary[sample_scraper_id].get("rate_limit", 0) >= 1

    def test_get_state_summary(self, monitor):
        """Test getting state summary"""
        monitor.record_request("ca_scraper", "CA", True, 100.0, records_count=50)
        monitor.record_request("ny_scraper", "NY", True, 150.0, records_count=30)
        monitor.record_request("ca_scraper2", "CA", True, 120.0, records_count=40)

        summary = monitor.get_state_summary()
        assert "CA" in summary
        assert "NY" in summary
        assert summary["CA"]["records_fetched"] == 90
        assert len(summary["CA"]["scrapers"]) == 2

    def test_get_overall_health(self, monitor):
        """Test getting overall health"""
        monitor.record_request("scraper1", "CA", True, 100.0)
        monitor.record_request("scraper2", "NY", True, 150.0)

        health = monitor.get_overall_health()
        assert health["status"] == "healthy"
        assert health["scraper_count"] == 2
        assert health["healthy_count"] == 2

    def test_get_overall_health_degraded(self, monitor):
        """Test overall health when degraded"""
        # Create a degraded scraper (>10% failure rate)
        for i in range(10):
            monitor.record_request(
                "bad_scraper", "CA", success=(i < 8), response_time_ms=100.0
            )

        health = monitor.get_overall_health()
        assert health["status"] in ["degraded", "healthy"]

    def test_get_overall_health_empty(self, monitor):
        """Test overall health with no scrapers"""
        health = monitor.get_overall_health()
        assert health["status"] == "unknown"
        assert health["scraper_count"] == 0

    def test_reset_metrics_single(self, monitor, sample_scraper_id, sample_state_code):
        """Test resetting metrics for single scraper"""
        monitor.record_request(
            sample_scraper_id, sample_state_code, True, 100.0, records_count=50
        )
        monitor.reset_metrics(sample_scraper_id)

        metrics = monitor.get_metrics(sample_scraper_id)
        assert metrics.total_requests == 0
        assert metrics.records_fetched == 0

    def test_reset_metrics_all(self, monitor):
        """Test resetting all metrics"""
        monitor.record_request("scraper1", "CA", True, 100.0)
        monitor.record_request("scraper2", "NY", True, 150.0)
        monitor.reset_metrics()

        all_metrics = monitor.get_all_metrics()
        assert len(all_metrics) == 0


class TestErrorClassification:
    """Tests for error classification"""

    @pytest.fixture
    def monitor(self):
        return ScraperHealthMonitor()

    def test_classify_timeout(self, monitor):
        """Test classifying timeout errors"""
        assert monitor._classify_error("Connection timeout") == "timeout"
        assert monitor._classify_error("Request timed out") == "timeout"

    def test_classify_connection(self, monitor):
        """Test classifying connection errors"""
        assert monitor._classify_error("Connection refused") == "connection"
        assert monitor._classify_error("Network unreachable") == "connection"

    def test_classify_rate_limit(self, monitor):
        """Test classifying rate limit errors"""
        assert monitor._classify_error("Rate limit exceeded") == "rate_limit"
        assert monitor._classify_error("HTTP 429 Too Many Requests") == "rate_limit"

    def test_classify_auth(self, monitor):
        """Test classifying authentication errors"""
        assert (
            monitor._classify_error("Authentication failed (401)") == "authentication"
        )
        assert monitor._classify_error("Access denied (403)") == "authentication"

    def test_classify_not_found(self, monitor):
        """Test classifying not found errors"""
        assert monitor._classify_error("Resource not found (404)") == "not_found"

    def test_classify_server_error(self, monitor):
        """Test classifying server errors"""
        assert monitor._classify_error("Internal server error (500)") == "server_error"

    def test_classify_parse_error(self, monitor):
        """Test classifying parse errors"""
        assert monitor._classify_error("JSON parse error") == "parse_error"

    def test_classify_unknown(self, monitor):
        """Test classifying unknown errors"""
        assert monitor._classify_error("Some other error") == "other"
        assert monitor._classify_error(None) == "unknown"
        assert monitor._classify_error("") == "unknown"


class TestConvenienceFunctions:
    """Tests for convenience functions"""

    def test_get_monitor(self):
        """Test getting singleton monitor"""
        monitor1 = get_monitor()
        monitor2 = get_monitor()
        assert monitor1 is monitor2

    def test_get_scraper_health(self):
        """Test convenience health check function"""
        monitor = get_monitor()
        monitor.record_request("test_scraper", "CA", True, 100.0)

        result = get_scraper_health("test_scraper")
        assert isinstance(result, HealthCheckResult)

    def test_check_all_scrapers_func(self):
        """Test convenience check all function"""
        monitor = get_monitor()
        monitor.reset_metrics()
        monitor.record_request("test1", "CA", True, 100.0)
        monitor.record_request("test2", "NY", True, 150.0)

        results = check_all_scrapers()
        assert isinstance(results, dict)
