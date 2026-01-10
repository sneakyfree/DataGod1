"""
Comprehensive tests for the Metrics Collector.

Tests cover:
- MetricType enum
- Metric dataclass
- AggregatedMetric dataclass
- MetricsCollector class
- Recording metrics
- Aggregation
- Histogram percentiles
- Export functions
"""

import pytest
from datetime import datetime, timedelta
from datagod.monitoring.metrics_collector import (
    MetricType,
    Metric,
    AggregatedMetric,
    MetricsCollector,
    get_collector,
    record_metric,
    get_metrics,
)


class TestMetricTypeEnum:
    """Tests for MetricType enum"""

    def test_all_types_exist(self):
        """Test that all metric types are defined"""
        assert MetricType.COUNTER is not None
        assert MetricType.GAUGE is not None
        assert MetricType.HISTOGRAM is not None
        assert MetricType.TIMER is not None

    def test_type_values(self):
        """Test metric type string values"""
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"
        assert MetricType.TIMER.value == "timer"


class TestMetric:
    """Tests for Metric dataclass"""

    def test_create_metric(self):
        """Test creating a metric"""
        metric = Metric(
            name="test.metric",
            value=100.0,
            metric_type=MetricType.GAUGE
        )
        assert metric.name == "test.metric"
        assert metric.value == 100.0
        assert metric.metric_type == MetricType.GAUGE

    def test_metric_with_tags(self):
        """Test metric with tags"""
        metric = Metric(
            name="test.metric",
            value=50.0,
            metric_type=MetricType.COUNTER,
            tags={"state": "CA", "county": "Los Angeles"}
        )
        assert metric.tags["state"] == "CA"

    def test_metric_with_unit(self):
        """Test metric with unit"""
        metric = Metric(
            name="response_time",
            value=150.0,
            metric_type=MetricType.TIMER,
            unit="ms"
        )
        assert metric.unit == "ms"

    def test_metric_to_dict(self):
        """Test converting metric to dictionary"""
        metric = Metric(
            name="test",
            value=100.0,
            metric_type=MetricType.GAUGE,
            tags={"env": "prod"},
            unit="count"
        )
        result = metric.to_dict()
        assert result['name'] == "test"
        assert result['value'] == 100.0
        assert result['type'] == "gauge"
        assert result['tags'] == {"env": "prod"}


class TestAggregatedMetric:
    """Tests for AggregatedMetric dataclass"""

    def test_create_aggregated(self):
        """Test creating aggregated metric"""
        agg = AggregatedMetric(
            name="test",
            metric_type=MetricType.GAUGE,
            count=100,
            sum_value=500.0,
            min_value=1.0,
            max_value=10.0,
            avg_value=5.0,
            std_dev=2.5,
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now()
        )
        assert agg.count == 100
        assert agg.avg_value == 5.0

    def test_aggregated_to_dict(self):
        """Test converting aggregated metric to dictionary"""
        agg = AggregatedMetric(
            name="test",
            metric_type=MetricType.GAUGE,
            count=10,
            sum_value=100.0,
            min_value=5.0,
            max_value=15.0,
            avg_value=10.0,
            std_dev=3.0,
            start_time=datetime.now(),
            end_time=datetime.now()
        )
        result = agg.to_dict()
        assert result['count'] == 10
        assert result['avg'] == 10.0
        assert 'start_time' in result


class TestMetricsCollector:
    """Tests for MetricsCollector class"""

    @pytest.fixture
    def collector(self):
        """Create fresh collector instance"""
        return MetricsCollector()

    def test_collector_initialization(self, collector):
        """Test collector initialization"""
        assert collector.retention == timedelta(days=7)

    def test_custom_retention(self):
        """Test collector with custom retention"""
        collector = MetricsCollector(retention_days=30)
        assert collector.retention == timedelta(days=30)

    def test_record_gauge(self, collector):
        """Test recording a gauge metric"""
        collector.gauge("cpu.usage", 75.5, tags={"host": "server1"})
        metrics = collector.get_metrics("cpu.usage")
        assert len(metrics) == 1
        assert metrics[0].value == 75.5

    def test_record_counter(self, collector):
        """Test recording counter metric"""
        collector.increment("requests.total")
        collector.increment("requests.total")
        collector.increment("requests.total", value=5)

        value = collector.get_counter_value("requests.total")
        assert value == 7.0

    def test_counter_with_tags(self, collector):
        """Test counter with different tags"""
        collector.increment("requests", tags={"endpoint": "/api/v1"})
        collector.increment("requests", tags={"endpoint": "/api/v2"})
        collector.increment("requests", tags={"endpoint": "/api/v1"})

        v1 = collector.get_counter_value("requests", {"endpoint": "/api/v1"})
        v2 = collector.get_counter_value("requests", {"endpoint": "/api/v2"})
        assert v1 == 2.0
        assert v2 == 1.0

    def test_record_histogram(self, collector):
        """Test recording histogram metric"""
        for i in range(100):
            collector.histogram("response_time", i * 10)

        percentiles = collector.get_histogram_percentiles("response_time")
        assert "p50" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles

    def test_record_timer(self, collector):
        """Test recording timer metric"""
        collector.timer("api.latency", 150.5, tags={"endpoint": "/users"})
        metrics = collector.get_metrics("api.latency")
        assert len(metrics) == 1
        assert metrics[0].unit == "ms"

    def test_get_metrics_with_time_filter(self, collector):
        """Test getting metrics with time filter"""
        collector.gauge("test", 1.0)

        # Get metrics from the last hour
        start = datetime.now() - timedelta(hours=1)
        metrics = collector.get_metrics("test", start_time=start)
        assert len(metrics) == 1

        # Get metrics from the future (should be empty)
        future = datetime.now() + timedelta(hours=1)
        metrics = collector.get_metrics("test", start_time=future)
        assert len(metrics) == 0

    def test_get_metrics_with_tag_filter(self, collector):
        """Test getting metrics with tag filter"""
        collector.gauge("cpu", 75.0, tags={"host": "server1"})
        collector.gauge("cpu", 80.0, tags={"host": "server2"})
        collector.gauge("cpu", 85.0, tags={"host": "server1"})

        metrics = collector.get_metrics("cpu", tags={"host": "server1"})
        assert len(metrics) == 2

    def test_aggregate_metrics(self, collector):
        """Test aggregating metrics"""
        for i in range(10):
            collector.gauge("test.value", float(i))

        agg = collector.aggregate("test.value")
        assert agg is not None
        assert agg.count == 10
        assert agg.min_value == 0.0
        assert agg.max_value == 9.0
        assert agg.avg_value == 4.5

    def test_aggregate_with_window(self, collector):
        """Test aggregating with time window"""
        for i in range(5):
            collector.gauge("test", float(i))

        agg = collector.aggregate("test", window=timedelta(hours=1))
        assert agg is not None
        assert agg.count == 5

    def test_aggregate_no_data(self, collector):
        """Test aggregating with no data"""
        agg = collector.aggregate("nonexistent")
        assert agg is None

    def test_histogram_percentiles(self, collector):
        """Test histogram percentile calculation"""
        # Record 100 values from 0 to 99
        for i in range(100):
            collector.histogram("latency", float(i))

        percentiles = collector.get_histogram_percentiles("latency")
        assert percentiles["p50"] >= 49.0
        assert percentiles["p95"] >= 94.0
        assert percentiles["p99"] >= 98.0

    def test_histogram_custom_percentiles(self, collector):
        """Test histogram with custom percentiles"""
        for i in range(100):
            collector.histogram("test", float(i))

        percentiles = collector.get_histogram_percentiles("test", [0.25, 0.75])
        assert "p25" in percentiles
        assert "p75" in percentiles

    def test_histogram_empty(self, collector):
        """Test histogram percentiles with no data"""
        percentiles = collector.get_histogram_percentiles("empty")
        assert percentiles == {}

    def test_get_all_metric_names(self, collector):
        """Test getting all metric names"""
        collector.gauge("metric1", 1.0)
        collector.gauge("metric2", 2.0)
        collector.increment("metric3", 3.0)

        names = collector.get_all_metric_names()
        assert "metric1" in names
        assert "metric2" in names
        assert "metric3" in names

    def test_get_metrics_by_prefix(self, collector):
        """Test getting metrics by prefix"""
        collector.gauge("scraper.requests", 100)
        collector.gauge("scraper.latency", 50)
        collector.gauge("api.requests", 200)

        scraper_metrics = collector.get_metrics_by_prefix("scraper")
        assert "scraper.requests" in scraper_metrics
        assert "scraper.latency" in scraper_metrics
        assert "api.requests" not in scraper_metrics

    def test_get_summary(self, collector):
        """Test getting summary"""
        collector.gauge("scraper.test1", 1.0)
        collector.gauge("scraper.test2", 2.0)
        collector.gauge("api.test", 3.0)
        collector.increment("counter.test")

        summary = collector.get_summary()
        assert summary['metric_names'] >= 3
        assert 'by_category' in summary

    def test_cleanup_old_metrics(self, collector):
        """Test cleaning up old metrics"""
        # Record metrics
        collector.gauge("test", 1.0)

        # Manually set old timestamp (for testing)
        old_time = datetime.now() - timedelta(days=30)
        for m in collector._metrics["test"]:
            m.timestamp = old_time

        collector.cleanup_old_metrics()
        assert len(collector.get_metrics("test")) == 0

    def test_export_prometheus(self, collector):
        """Test exporting in Prometheus format"""
        collector.gauge("cpu_usage", 75.5, tags={"host": "server1"})
        collector.gauge("memory_usage", 60.0)

        output = collector.export_prometheus()
        assert "cpu_usage" in output
        assert "memory_usage" in output
        assert "gauge" in output

    def test_export_json(self, collector):
        """Test exporting as JSON"""
        collector.gauge("test1", 1.0)
        collector.gauge("test2", 2.0)

        export = collector.export_json()
        assert 'metrics' in export
        assert 'summary' in export
        assert 'exported_at' in export

    def test_clear(self, collector):
        """Test clearing all metrics"""
        collector.gauge("test1", 1.0)
        collector.gauge("test2", 2.0)
        collector.increment("counter")

        collector.clear()

        assert len(collector.get_all_metric_names()) == 0


class TestTimeFunction:
    """Tests for time_function decorator"""

    @pytest.fixture
    def collector(self):
        return MetricsCollector()

    def test_time_function_decorator(self, collector):
        """Test timing a function"""
        @collector.time_function("my_function")
        def slow_function():
            import time
            time.sleep(0.01)  # 10ms
            return "result"

        result = slow_function()
        assert result == "result"

        metrics = collector.get_metrics("my_function")
        assert len(metrics) == 1
        assert metrics[0].value >= 10  # At least 10ms


class TestConvenienceFunctions:
    """Tests for convenience functions"""

    def test_get_collector(self):
        """Test getting singleton collector"""
        collector1 = get_collector()
        collector2 = get_collector()
        assert collector1 is collector2

    def test_record_metric_func(self):
        """Test convenience record function"""
        record_metric("test.convenience", 100.0, MetricType.GAUGE)
        metrics = get_metrics("test.convenience")
        assert len(metrics) >= 1

    def test_get_metrics_func(self):
        """Test convenience get function"""
        collector = get_collector()
        collector.gauge("get.test", 50.0)

        metrics = get_metrics("get.test")
        assert isinstance(metrics, list)
