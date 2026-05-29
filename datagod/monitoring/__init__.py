"""
Monitoring Framework

Real-time monitoring for scraper health, data quality, and system performance.

Modules:
- scraper_health: Scraper execution monitoring and health checks
- metrics_collector: Metrics collection and aggregation
- alerts: Alert configuration and notification
"""

from datagod.monitoring.alerts import (
    Alert,
    AlertManager,
    AlertRule,
    AlertSeverity,
    check_alert_rules,
    send_alert,
)
from datagod.monitoring.data_quality_dashboard import (
    CoverageMetrics,
    DataQualityDashboard,
    ErrorLogEntry,
    FreshnessStatus,
    QualityGrade,
    QualityScore,
    QuotaStatus,
    get_dashboard,
    get_dashboard_summary,
    log_data_error,
    update_coverage,
)
from datagod.monitoring.metrics_collector import (
    Metric,
    MetricsCollector,
    MetricType,
    get_metrics,
    record_metric,
)
from datagod.monitoring.scraper_health import (
    HealthStatus,
    ScraperHealthMonitor,
    ScraperMetrics,
    check_all_scrapers,
    get_scraper_health,
)

__all__ = [
    # Scraper health
    "ScraperHealthMonitor",
    "HealthStatus",
    "ScraperMetrics",
    "get_scraper_health",
    "check_all_scrapers",
    # Metrics
    "MetricsCollector",
    "MetricType",
    "Metric",
    "get_metrics",
    "record_metric",
    # Alerts
    "AlertManager",
    "AlertSeverity",
    "Alert",
    "AlertRule",
    "send_alert",
    "check_alert_rules",
    # Dashboard
    "DataQualityDashboard",
    "CoverageMetrics",
    "QualityScore",
    "QualityGrade",
    "FreshnessStatus",
    "ErrorLogEntry",
    "QuotaStatus",
    "get_dashboard",
    "update_coverage",
    "log_data_error",
    "get_dashboard_summary",
]
