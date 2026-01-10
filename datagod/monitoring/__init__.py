"""
Monitoring Framework

Real-time monitoring for scraper health, data quality, and system performance.

Modules:
- scraper_health: Scraper execution monitoring and health checks
- metrics_collector: Metrics collection and aggregation
- alerts: Alert configuration and notification
"""

from datagod.monitoring.scraper_health import (
    ScraperHealthMonitor,
    HealthStatus,
    ScraperMetrics,
    get_scraper_health,
    check_all_scrapers,
)

from datagod.monitoring.metrics_collector import (
    MetricsCollector,
    MetricType,
    Metric,
    get_metrics,
    record_metric,
)

from datagod.monitoring.alerts import (
    AlertManager,
    AlertSeverity,
    Alert,
    AlertRule,
    send_alert,
    check_alert_rules,
)

from datagod.monitoring.data_quality_dashboard import (
    DataQualityDashboard,
    CoverageMetrics,
    QualityScore,
    QualityGrade,
    FreshnessStatus,
    ErrorLogEntry,
    QuotaStatus,
    get_dashboard,
    update_coverage,
    log_data_error,
    get_dashboard_summary,
)

__all__ = [
    # Scraper health
    'ScraperHealthMonitor',
    'HealthStatus',
    'ScraperMetrics',
    'get_scraper_health',
    'check_all_scrapers',
    # Metrics
    'MetricsCollector',
    'MetricType',
    'Metric',
    'get_metrics',
    'record_metric',
    # Alerts
    'AlertManager',
    'AlertSeverity',
    'Alert',
    'AlertRule',
    'send_alert',
    'check_alert_rules',
    # Dashboard
    'DataQualityDashboard',
    'CoverageMetrics',
    'QualityScore',
    'QualityGrade',
    'FreshnessStatus',
    'ErrorLogEntry',
    'QuotaStatus',
    'get_dashboard',
    'update_coverage',
    'log_data_error',
    'get_dashboard_summary',
]
