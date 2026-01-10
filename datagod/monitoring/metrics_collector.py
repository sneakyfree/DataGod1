"""
Metrics Collector

Collects, aggregates, and stores system metrics.

Features:
- Time-series metrics storage
- Aggregation functions (avg, sum, min, max)
- Metric tags and labels
- Export to various formats
"""

import logging
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from enum import Enum
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"      # Monotonically increasing value
    GAUGE = "gauge"          # Point-in-time value
    HISTOGRAM = "histogram"  # Distribution of values
    TIMER = "timer"          # Duration measurements


@dataclass
class Metric:
    """A single metric data point"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'value': self.value,
            'type': self.metric_type.value,
            'timestamp': self.timestamp.isoformat(),
            'tags': self.tags,
            'unit': self.unit,
        }


@dataclass
class AggregatedMetric:
    """Aggregated metric over a time window"""
    name: str
    metric_type: MetricType
    count: int
    sum_value: float
    min_value: float
    max_value: float
    avg_value: float
    std_dev: float
    start_time: datetime
    end_time: datetime
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'type': self.metric_type.value,
            'count': self.count,
            'sum': round(self.sum_value, 4),
            'min': round(self.min_value, 4),
            'max': round(self.max_value, 4),
            'avg': round(self.avg_value, 4),
            'std_dev': round(self.std_dev, 4),
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'tags': self.tags,
        }


class MetricsCollector:
    """
    Collects and aggregates metrics.

    Features:
    - Store time-series metrics
    - Aggregate over time windows
    - Filter by tags
    - Export metrics
    """

    # Metric name prefixes for different categories
    PREFIX_SCRAPER = "scraper"
    PREFIX_API = "api"
    PREFIX_DB = "database"
    PREFIX_VALIDATION = "validation"
    PREFIX_SYSTEM = "system"

    # Default retention period (7 days)
    DEFAULT_RETENTION_DAYS = 7

    def __init__(self, retention_days: int = DEFAULT_RETENTION_DAYS):
        """
        Initialize the metrics collector.

        Args:
            retention_days: Days to retain metrics
        """
        self.retention = timedelta(days=retention_days)

        # Metrics storage: {metric_name: [Metric, ...]}
        self._metrics: Dict[str, List[Metric]] = defaultdict(list)

        # Counter values: {metric_name: {tags_key: value}}
        self._counters: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

        # Histograms: {metric_name: {tags_key: [values]}}
        self._histograms: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))

    def record(self, name: str, value: float,
               metric_type: MetricType = MetricType.GAUGE,
               tags: Dict[str, str] = None,
               unit: str = ""):
        """
        Record a metric.

        Args:
            name: Metric name
            value: Metric value
            metric_type: Type of metric
            tags: Optional tags/labels
            unit: Unit of measurement
        """
        tags = tags or {}
        tags_key = self._tags_to_key(tags)

        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            tags=tags,
            unit=unit
        )

        self._metrics[name].append(metric)

        # Handle type-specific storage
        if metric_type == MetricType.COUNTER:
            self._counters[name][tags_key] += value
        elif metric_type == MetricType.HISTOGRAM:
            self._histograms[name][tags_key].append(value)

        logger.debug(f"Recorded metric: {name}={value} ({metric_type.value})")

    def increment(self, name: str, value: float = 1.0,
                  tags: Dict[str, str] = None):
        """Increment a counter metric"""
        self.record(name, value, MetricType.COUNTER, tags)

    def gauge(self, name: str, value: float,
              tags: Dict[str, str] = None, unit: str = ""):
        """Record a gauge metric"""
        self.record(name, value, MetricType.GAUGE, tags, unit)

    def histogram(self, name: str, value: float,
                  tags: Dict[str, str] = None, unit: str = ""):
        """Record a histogram metric"""
        self.record(name, value, MetricType.HISTOGRAM, tags, unit)

    def timer(self, name: str, duration_ms: float,
              tags: Dict[str, str] = None):
        """Record a timer metric"""
        self.record(name, duration_ms, MetricType.TIMER, tags, "ms")

    def time_function(self, name: str, tags: Dict[str, str] = None):
        """
        Decorator to time function execution.

        Usage:
            @collector.time_function("my_function")
            def my_function():
                pass
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration_ms = (time.time() - start) * 1000
                    self.timer(name, duration_ms, tags)
            return wrapper
        return decorator

    def get_metrics(self, name: str,
                    start_time: datetime = None,
                    end_time: datetime = None,
                    tags: Dict[str, str] = None) -> List[Metric]:
        """
        Get metrics by name and optional filters.

        Args:
            name: Metric name
            start_time: Filter by start time
            end_time: Filter by end time
            tags: Filter by tags

        Returns:
            List of matching metrics
        """
        metrics = self._metrics.get(name, [])

        # Filter by time
        if start_time:
            metrics = [m for m in metrics if m.timestamp >= start_time]
        if end_time:
            metrics = [m for m in metrics if m.timestamp <= end_time]

        # Filter by tags
        if tags:
            metrics = [m for m in metrics
                      if all(m.tags.get(k) == v for k, v in tags.items())]

        return metrics

    def get_counter_value(self, name: str,
                          tags: Dict[str, str] = None) -> float:
        """Get current counter value"""
        tags_key = self._tags_to_key(tags or {})
        return self._counters.get(name, {}).get(tags_key, 0.0)

    def aggregate(self, name: str,
                  window: timedelta = None,
                  tags: Dict[str, str] = None) -> Optional[AggregatedMetric]:
        """
        Aggregate metrics over a time window.

        Args:
            name: Metric name
            window: Time window (default: all data)
            tags: Filter by tags

        Returns:
            AggregatedMetric or None if no data
        """
        end_time = datetime.now()
        start_time = end_time - window if window else datetime.min

        metrics = self.get_metrics(name, start_time, end_time, tags)

        if not metrics:
            return None

        values = [m.value for m in metrics]

        return AggregatedMetric(
            name=name,
            metric_type=metrics[0].metric_type,
            count=len(values),
            sum_value=sum(values),
            min_value=min(values),
            max_value=max(values),
            avg_value=statistics.mean(values),
            std_dev=statistics.stdev(values) if len(values) > 1 else 0.0,
            start_time=start_time,
            end_time=end_time,
            tags=tags or {},
        )

    def get_histogram_percentiles(self, name: str,
                                   percentiles: List[float] = None,
                                   tags: Dict[str, str] = None) -> Dict[str, float]:
        """
        Get histogram percentiles.

        Args:
            name: Metric name
            percentiles: List of percentiles (e.g., [0.5, 0.95, 0.99])
            tags: Filter by tags

        Returns:
            Dictionary of percentile values
        """
        percentiles = percentiles or [0.5, 0.75, 0.9, 0.95, 0.99]
        tags_key = self._tags_to_key(tags or {})
        values = self._histograms.get(name, {}).get(tags_key, [])

        if not values:
            return {}

        sorted_values = sorted(values)
        result = {}

        for p in percentiles:
            idx = int(len(sorted_values) * p)
            idx = min(idx, len(sorted_values) - 1)
            result[f"p{int(p * 100)}"] = sorted_values[idx]

        return result

    def get_all_metric_names(self) -> List[str]:
        """Get all metric names"""
        return list(self._metrics.keys())

    def get_metrics_by_prefix(self, prefix: str) -> Dict[str, List[Metric]]:
        """Get all metrics matching a prefix"""
        return {name: metrics
                for name, metrics in self._metrics.items()
                if name.startswith(prefix)}

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        summary = {
            'total_metrics': sum(len(m) for m in self._metrics.values()),
            'metric_names': len(self._metrics),
            'counters': len(self._counters),
            'histograms': len(self._histograms),
            'by_category': {},
        }

        # Group by category (prefix)
        for name in self._metrics.keys():
            prefix = name.split('.')[0] if '.' in name else name
            if prefix not in summary['by_category']:
                summary['by_category'][prefix] = 0
            summary['by_category'][prefix] += len(self._metrics[name])

        return summary

    def cleanup_old_metrics(self):
        """Remove metrics older than retention period"""
        cutoff = datetime.now() - self.retention
        removed = 0

        for name in list(self._metrics.keys()):
            original_count = len(self._metrics[name])
            self._metrics[name] = [m for m in self._metrics[name]
                                   if m.timestamp > cutoff]
            removed += original_count - len(self._metrics[name])

            # Remove empty entries
            if not self._metrics[name]:
                del self._metrics[name]

        if removed > 0:
            logger.info(f"Cleaned up {removed} old metrics")

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []

        for name, metrics in self._metrics.items():
            if not metrics:
                continue

            # Get latest metric
            latest = metrics[-1]

            # Format tags
            if latest.tags:
                tags_str = ",".join(f'{k}="{v}"' for k, v in latest.tags.items())
                metric_line = f'{name}{{{tags_str}}} {latest.value}'
            else:
                metric_line = f'{name} {latest.value}'

            lines.append(f"# TYPE {name} {latest.metric_type.value}")
            lines.append(metric_line)

        return "\n".join(lines)

    def export_json(self) -> Dict[str, Any]:
        """Export all metrics as JSON"""
        return {
            'metrics': {name: [m.to_dict() for m in metrics]
                       for name, metrics in self._metrics.items()},
            'counters': dict(self._counters),
            'summary': self.get_summary(),
            'exported_at': datetime.now().isoformat(),
        }

    def clear(self):
        """Clear all metrics"""
        self._metrics.clear()
        self._counters.clear()
        self._histograms.clear()

    def _tags_to_key(self, tags: Dict[str, str]) -> str:
        """Convert tags to a hashable key"""
        if not tags:
            return ""
        return "|".join(f"{k}={v}" for k, v in sorted(tags.items()))


# Singleton instance
_collector_instance: Optional[MetricsCollector] = None


def get_collector() -> MetricsCollector:
    """Get the singleton metrics collector"""
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = MetricsCollector()
    return _collector_instance


def record_metric(name: str, value: float,
                  metric_type: MetricType = MetricType.GAUGE,
                  tags: Dict[str, str] = None):
    """Convenience function to record a metric"""
    get_collector().record(name, value, metric_type, tags)


def get_metrics(name: str,
                start_time: datetime = None,
                end_time: datetime = None) -> List[Metric]:
    """Convenience function to get metrics"""
    return get_collector().get_metrics(name, start_time, end_time)
