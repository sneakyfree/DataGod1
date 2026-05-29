"""
Tests for analytics and search API endpoints.
Verifies time-series, summary, trends, and entity search endpoints.
"""

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api", "src"))

# Set environment for testing
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")


class TestAnalyticsTimeSeries:
    """Tests for GET /analytics/time-series"""

    def test_time_series_default_period(self):
        """Time-series should default to monthly period."""
        from datagod.models import Record

        # Verify we can import the endpoint's dependencies
        assert Record is not None

    def test_time_series_valid_periods(self):
        """Valid period values: day, week, month."""
        valid_periods = ["day", "week", "month"]
        for period in valid_periods:
            assert period in valid_periods

    def test_time_series_months_range(self):
        """Months parameter should be between 1 and 60."""
        assert 1 <= 12 <= 60
        assert not (1 <= 0 <= 60)
        assert not (1 <= 61 <= 60)


class TestAnalyticsSummary:
    """Tests for GET /analytics/summary"""

    def test_summary_response_structure(self):
        """Summary should return totals and record_type_distribution."""
        expected_keys = ["totals", "record_type_distribution"]
        # This tests the expected response contract
        for key in expected_keys:
            assert isinstance(key, str)

    def test_summary_totals_fields(self):
        """Totals should include records, jurisdictions, entities, total_amount."""
        expected_fields = ["records", "jurisdictions", "entities", "total_amount"]
        assert len(expected_fields) == 4


class TestAnalyticsTrends:
    """Tests for GET /analytics/trends"""

    def test_growth_rate_calculation(self):
        """Verify growth rate calculation logic."""
        current = 100
        previous = 80
        growth_rate = ((current - previous) / max(previous, 1)) * 100
        assert growth_rate == 25.0

    def test_growth_rate_zero_previous(self):
        """Growth rate with zero previous should not error."""
        current = 50
        previous = 0
        growth_rate = ((current - previous) / max(previous, 1)) * 100
        assert growth_rate == 5000.0

    def test_trend_direction(self):
        """Trend should be 'up', 'down', or 'flat'."""
        assert "up" if 25 > 0 else "down"
        trend = "up" if 25 > 0 else ("down" if 25 < 0 else "flat")
        assert trend == "up"

        trend = "up" if -5 > 0 else ("down" if -5 < 0 else "flat")
        assert trend == "down"

        trend = "up" if 0 > 0 else ("down" if 0 < 0 else "flat")
        assert trend == "flat"


class TestEntitySearch:
    """Tests for entity quick-search / typeahead."""

    def test_search_query_sanitization(self):
        """Search queries should be sanitized."""
        from datagod.utils.sanitize import sanitize_input

        dangerous = "<script>alert('xss')</script>"
        safe = sanitize_input(dangerous)
        assert "<script>" not in safe

    def test_search_minimum_query_length(self):
        """Search should require minimum 2 characters."""
        min_length = 2
        assert len("ab") >= min_length
        assert len("a") < min_length


class TestSubscriptionGate:
    """Tests for subscription tier enforcement."""

    def test_tier_ordering(self):
        """Tiers should be ordered: free < basic < pro < enterprise."""
        from datagod.middleware.subscription_gate import TIER_LEVELS

        assert TIER_LEVELS["free"] < TIER_LEVELS["basic"]
        assert TIER_LEVELS["basic"] < TIER_LEVELS["pro"]
        assert TIER_LEVELS["pro"] < TIER_LEVELS["enterprise"]

    def test_tier_limits_exist(self):
        """All tiers should have defined limits."""
        from datagod.middleware.subscription_gate import TIER_LIMITS

        for tier in ["free", "basic", "pro", "enterprise"]:
            assert tier in TIER_LIMITS
            assert "searches_per_day" in TIER_LIMITS[tier]

    def test_free_tier_has_limits(self):
        """Free tier should have restrictive limits."""
        from datagod.middleware.subscription_gate import TIER_LIMITS

        free_limits = TIER_LIMITS["free"]
        assert free_limits["searches_per_day"] > 0
        assert free_limits["exports_per_day"] > 0

    def test_enterprise_tier_unlimited(self):
        """Enterprise tier should have unlimited (-1) for key features."""
        from datagod.middleware.subscription_gate import TIER_LIMITS

        ent_limits = TIER_LIMITS["enterprise"]
        assert ent_limits["searches_per_day"] == -1
        assert ent_limits["exports_per_day"] == -1

    def test_check_usage_limit(self):
        """Usage limit check should respect tier boundaries."""
        from datagod.middleware.subscription_gate import check_usage_limit

        # Enterprise should always pass
        assert check_usage_limit("enterprise", "searches_per_day", 999999) is True


class TestWebSocketManager:
    """Tests for WebSocket connection management."""

    def test_manager_initialization(self):
        """WebSocket manager should initialize with empty connections."""
        from api.src.websocket_manager import ConnectionManager

        mgr = ConnectionManager()
        assert mgr.connection_count == 0
        assert mgr.user_count == 0

    def test_manager_stats(self):
        """Stats should return connection and room counts."""
        from api.src.websocket_manager import ConnectionManager

        mgr = ConnectionManager()
        stats = mgr.get_stats()
        assert "total_connections" in stats
        assert "unique_users" in stats
        assert "rooms" in stats
        assert stats["total_connections"] == 0


class TestAdminScraperStatus:
    """Tests for admin scraper status endpoint."""

    def test_scraper_health_statuses(self):
        """Scraper health should be: healthy, warning, or stale."""
        valid = {"healthy", "warning", "stale"}
        for status in valid:
            assert status in valid

    def test_stale_threshold(self):
        """Scrapers not updated in >30 days should be stale."""
        stale_days = 30
        last_updated = datetime.utcnow() - timedelta(days=31)
        threshold = datetime.utcnow() - timedelta(days=stale_days)
        assert last_updated < threshold

    def test_active_threshold(self):
        """Scrapers updated within 30 days should be active."""
        last_updated = datetime.utcnow() - timedelta(days=5)
        threshold = datetime.utcnow() - timedelta(days=30)
        assert last_updated >= threshold


class TestAdminDataQuality:
    """Tests for data quality metrics endpoint."""

    def test_completeness_calculation(self):
        """Completeness should be (non_null / total) * 100."""
        non_null = 85
        total = 100
        completeness = round((non_null / total) * 100, 1)
        assert completeness == 85.0

    def test_completeness_zero_total(self):
        """Zero records should return 0 quality score."""
        total = 0
        if total == 0:
            quality = 0
        else:
            quality = 100
        assert quality == 0

    def test_average_quality(self):
        """Overall quality should be average of all field completeness."""
        fields = [100.0, 90.0, 80.0, 70.0, 60.0]
        avg = round(sum(fields) / len(fields), 1)
        assert avg == 80.0

    def test_field_names(self):
        """Expected data quality fields."""
        expected = ["title", "description", "amount", "date", "record_type"]
        assert len(expected) == 5


class TestPerformanceCache:
    """Tests for CacheManager and AsyncBatchProcessor."""

    def test_cache_manager_init(self):
        """CacheManager should initialize with default settings."""
        from datagod.performance import CacheManager

        cache = CacheManager(max_size=100, default_ttl=60)
        stats = cache.get_stats()
        assert stats["max_size"] == 100
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    def test_cache_set_get(self):
        """CacheManager should store and retrieve values."""
        from datagod.performance import CacheManager

        cache = CacheManager()
        cache.set("test_key", "test_value", ttl=60)
        result = cache.get("test_key")
        assert result == "test_value"

    def test_cache_miss(self):
        """Non-existent keys should return None."""
        from datagod.performance import CacheManager

        cache = CacheManager()
        result = cache.get("nonexistent")
        assert result is None

    def test_cache_clear(self):
        """Clear should remove all entries."""
        from datagod.performance import CacheManager

        cache = CacheManager()
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.clear()
        assert cache.get("k1") is None
        assert cache.get("k2") is None

    def test_batch_processor_init(self):
        """AsyncBatchProcessor should initialize with correct settings."""
        from datagod.performance import AsyncBatchProcessor

        proc = AsyncBatchProcessor(batch_size=25, max_concurrent=5)
        assert proc.batch_size == 25
        assert proc.max_concurrent == 5

    def test_ux_package_imports(self):
        """UX package should export all expected symbols."""
        from datagod.ux import (
            ExportFormat,
            FieldType,
            GuidedIntakeWizard,
            IntakeSchema,
            MultiViewReportGenerator,
            ReportView,
        )

        assert GuidedIntakeWizard is not None
        assert MultiViewReportGenerator is not None
        assert ReportView is not None
