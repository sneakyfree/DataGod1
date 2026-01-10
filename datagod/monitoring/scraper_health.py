"""
Scraper Health Monitor

Monitors the health and performance of all scrapers.

Features:
- Real-time health status tracking
- Success/failure rate monitoring
- Response time tracking
- Data freshness monitoring
- API quota management
"""

import logging
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"          # All systems operational
    DEGRADED = "degraded"        # Some issues, still functional
    UNHEALTHY = "unhealthy"      # Significant issues
    CRITICAL = "critical"        # System down or major failure
    UNKNOWN = "unknown"          # Status not determined


@dataclass
class ScraperMetrics:
    """Metrics for a single scraper"""
    scraper_id: str
    state_code: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time_ms: float = 0.0
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    last_error_message: Optional[str] = None
    records_fetched: int = 0
    api_quota_used: int = 0
    api_quota_limit: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate"""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    @property
    def avg_response_time_ms(self) -> float:
        """Calculate average response time"""
        if self.successful_requests == 0:
            return 0.0
        return self.total_response_time_ms / self.successful_requests

    @property
    def quota_usage_percent(self) -> float:
        """Calculate API quota usage percentage"""
        if self.api_quota_limit == 0:
            return 0.0
        return (self.api_quota_used / self.api_quota_limit) * 100

    @property
    def health_status(self) -> HealthStatus:
        """Determine health status based on metrics"""
        # Critical: >50% failure rate or quota exceeded
        if self.failure_rate > 0.5 or self.quota_usage_percent > 100:
            return HealthStatus.CRITICAL

        # Unhealthy: >25% failure rate or >90% quota
        if self.failure_rate > 0.25 or self.quota_usage_percent > 90:
            return HealthStatus.UNHEALTHY

        # Degraded: >10% failure rate or >75% quota or slow response
        if (self.failure_rate > 0.10 or
            self.quota_usage_percent > 75 or
            self.avg_response_time_ms > 5000):
            return HealthStatus.DEGRADED

        # Healthy
        if self.total_requests > 0:
            return HealthStatus.HEALTHY

        return HealthStatus.UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'scraper_id': self.scraper_id,
            'state_code': self.state_code,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': round(self.success_rate, 4),
            'failure_rate': round(self.failure_rate, 4),
            'avg_response_time_ms': round(self.avg_response_time_ms, 2),
            'last_success_time': self.last_success_time.isoformat() if self.last_success_time else None,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'last_error_message': self.last_error_message,
            'records_fetched': self.records_fetched,
            'api_quota_used': self.api_quota_used,
            'api_quota_limit': self.api_quota_limit,
            'quota_usage_percent': round(self.quota_usage_percent, 2),
            'health_status': self.health_status.value,
            'updated_at': self.updated_at.isoformat(),
        }


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    scraper_id: str
    status: HealthStatus
    message: str
    checked_at: datetime = field(default_factory=datetime.now)
    response_time_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'scraper_id': self.scraper_id,
            'status': self.status.value,
            'message': self.message,
            'checked_at': self.checked_at.isoformat(),
            'response_time_ms': round(self.response_time_ms, 2),
            'details': self.details,
        }


class ScraperHealthMonitor:
    """
    Monitors scraper health and performance.

    Features:
    - Track success/failure rates
    - Monitor response times
    - Check data freshness
    - Manage API quotas
    - Generate health reports
    """

    # Default thresholds
    DEFAULT_FRESHNESS_HOURS = 24
    DEFAULT_RESPONSE_TIME_WARN_MS = 3000
    DEFAULT_RESPONSE_TIME_CRITICAL_MS = 10000
    DEFAULT_QUOTA_WARN_PERCENT = 75
    DEFAULT_QUOTA_CRITICAL_PERCENT = 90

    def __init__(self,
                 freshness_threshold_hours: int = DEFAULT_FRESHNESS_HOURS,
                 response_time_warn_ms: float = DEFAULT_RESPONSE_TIME_WARN_MS,
                 response_time_critical_ms: float = DEFAULT_RESPONSE_TIME_CRITICAL_MS):
        """
        Initialize the health monitor.

        Args:
            freshness_threshold_hours: Hours before data is considered stale
            response_time_warn_ms: Response time warning threshold
            response_time_critical_ms: Response time critical threshold
        """
        self.freshness_threshold = timedelta(hours=freshness_threshold_hours)
        self.response_time_warn = response_time_warn_ms
        self.response_time_critical = response_time_critical_ms

        # Metrics storage (in production, use Redis or database)
        self._metrics: Dict[str, ScraperMetrics] = {}
        self._health_history: List[HealthCheckResult] = []
        self._error_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def record_request(self, scraper_id: str, state_code: str,
                       success: bool, response_time_ms: float,
                       records_count: int = 0, error_message: str = None):
        """
        Record a scraper request.

        Args:
            scraper_id: Unique identifier for the scraper
            state_code: State code (e.g., 'CA', 'NY')
            success: Whether the request succeeded
            response_time_ms: Response time in milliseconds
            records_count: Number of records fetched
            error_message: Error message if failed
        """
        # Get or create metrics
        if scraper_id not in self._metrics:
            self._metrics[scraper_id] = ScraperMetrics(
                scraper_id=scraper_id,
                state_code=state_code
            )

        metrics = self._metrics[scraper_id]
        metrics.total_requests += 1
        metrics.updated_at = datetime.now()

        if success:
            metrics.successful_requests += 1
            metrics.total_response_time_ms += response_time_ms
            metrics.last_success_time = datetime.now()
            metrics.records_fetched += records_count
        else:
            metrics.failed_requests += 1
            metrics.last_failure_time = datetime.now()
            metrics.last_error_message = error_message

            # Track error types
            error_type = self._classify_error(error_message)
            self._error_counts[scraper_id][error_type] += 1

        logger.debug(f"Recorded request for {scraper_id}: success={success}, "
                    f"time={response_time_ms}ms, records={records_count}")

    def update_quota(self, scraper_id: str, used: int, limit: int):
        """
        Update API quota for a scraper.

        Args:
            scraper_id: Unique identifier for the scraper
            used: Current quota usage
            limit: Quota limit
        """
        if scraper_id in self._metrics:
            self._metrics[scraper_id].api_quota_used = used
            self._metrics[scraper_id].api_quota_limit = limit

    def get_metrics(self, scraper_id: str) -> Optional[ScraperMetrics]:
        """Get metrics for a specific scraper"""
        return self._metrics.get(scraper_id)

    def get_all_metrics(self) -> Dict[str, ScraperMetrics]:
        """Get metrics for all scrapers"""
        return self._metrics.copy()

    def check_health(self, scraper_id: str,
                     health_check_func: Callable[[], bool] = None) -> HealthCheckResult:
        """
        Check health of a specific scraper.

        Args:
            scraper_id: Unique identifier for the scraper
            health_check_func: Optional function to perform actual health check

        Returns:
            HealthCheckResult
        """
        metrics = self._metrics.get(scraper_id)

        if metrics is None:
            return HealthCheckResult(
                scraper_id=scraper_id,
                status=HealthStatus.UNKNOWN,
                message="No metrics available for this scraper"
            )

        # Perform actual health check if function provided
        check_start = time.time()
        if health_check_func:
            try:
                is_healthy = health_check_func()
                response_time = (time.time() - check_start) * 1000
                if not is_healthy:
                    return HealthCheckResult(
                        scraper_id=scraper_id,
                        status=HealthStatus.UNHEALTHY,
                        message="Health check function returned False",
                        response_time_ms=response_time
                    )
            except Exception as e:
                response_time = (time.time() - check_start) * 1000
                return HealthCheckResult(
                    scraper_id=scraper_id,
                    status=HealthStatus.CRITICAL,
                    message=f"Health check failed: {str(e)}",
                    response_time_ms=response_time
                )

        # Check based on metrics
        issues = []
        status = metrics.health_status

        # Check data freshness
        if metrics.last_success_time:
            age = datetime.now() - metrics.last_success_time
            if age > self.freshness_threshold:
                issues.append(f"Data is stale (last success {age.total_seconds() / 3600:.1f} hours ago)")
                if status == HealthStatus.HEALTHY:
                    status = HealthStatus.DEGRADED

        # Check response time
        if metrics.avg_response_time_ms > self.response_time_critical:
            issues.append(f"Critical response time ({metrics.avg_response_time_ms:.0f}ms)")
        elif metrics.avg_response_time_ms > self.response_time_warn:
            issues.append(f"Slow response time ({metrics.avg_response_time_ms:.0f}ms)")

        # Check failure rate
        if metrics.failure_rate > 0.1:
            issues.append(f"High failure rate ({metrics.failure_rate:.1%})")

        # Check quota
        if metrics.quota_usage_percent > self.DEFAULT_QUOTA_CRITICAL_PERCENT:
            issues.append(f"Quota critical ({metrics.quota_usage_percent:.1f}%)")
        elif metrics.quota_usage_percent > self.DEFAULT_QUOTA_WARN_PERCENT:
            issues.append(f"Quota warning ({metrics.quota_usage_percent:.1f}%)")

        message = "; ".join(issues) if issues else "All systems operational"

        result = HealthCheckResult(
            scraper_id=scraper_id,
            status=status,
            message=message,
            response_time_ms=(time.time() - check_start) * 1000,
            details={
                'success_rate': metrics.success_rate,
                'avg_response_time_ms': metrics.avg_response_time_ms,
                'quota_usage_percent': metrics.quota_usage_percent,
                'records_fetched': metrics.records_fetched,
            }
        )

        self._health_history.append(result)
        return result

    def check_all_scrapers(self) -> Dict[str, HealthCheckResult]:
        """Check health of all registered scrapers"""
        results = {}
        for scraper_id in self._metrics.keys():
            results[scraper_id] = self.check_health(scraper_id)
        return results

    def get_error_summary(self, scraper_id: str = None) -> Dict[str, Dict[str, int]]:
        """
        Get error summary by type.

        Args:
            scraper_id: Optional specific scraper (None for all)

        Returns:
            Dictionary of error counts by scraper and error type
        """
        if scraper_id:
            return {scraper_id: dict(self._error_counts.get(scraper_id, {}))}
        return {k: dict(v) for k, v in self._error_counts.items()}

    def get_state_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of health by state"""
        state_summary = defaultdict(lambda: {
            'scrapers': [],
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'records_fetched': 0,
            'health_status': HealthStatus.UNKNOWN.value,
        })

        for scraper_id, metrics in self._metrics.items():
            state = metrics.state_code
            state_summary[state]['scrapers'].append(scraper_id)
            state_summary[state]['total_requests'] += metrics.total_requests
            state_summary[state]['successful_requests'] += metrics.successful_requests
            state_summary[state]['failed_requests'] += metrics.failed_requests
            state_summary[state]['records_fetched'] += metrics.records_fetched

            # Determine overall state health (worst status wins)
            current_status = HealthStatus(state_summary[state]['health_status'])
            if self._status_priority(metrics.health_status) > self._status_priority(current_status):
                state_summary[state]['health_status'] = metrics.health_status.value

        # Calculate success rates
        for state, data in state_summary.items():
            if data['total_requests'] > 0:
                data['success_rate'] = data['successful_requests'] / data['total_requests']
            else:
                data['success_rate'] = 0.0

        return dict(state_summary)

    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health summary"""
        if not self._metrics:
            return {
                'status': HealthStatus.UNKNOWN.value,
                'message': 'No scrapers registered',
                'scraper_count': 0,
                'healthy_count': 0,
                'degraded_count': 0,
                'unhealthy_count': 0,
                'critical_count': 0,
            }

        status_counts = defaultdict(int)
        total_requests = 0
        total_successful = 0
        total_records = 0

        for metrics in self._metrics.values():
            status_counts[metrics.health_status] += 1
            total_requests += metrics.total_requests
            total_successful += metrics.successful_requests
            total_records += metrics.records_fetched

        # Determine overall status
        if status_counts[HealthStatus.CRITICAL] > 0:
            overall_status = HealthStatus.CRITICAL
        elif status_counts[HealthStatus.UNHEALTHY] > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif status_counts[HealthStatus.DEGRADED] > 0:
            overall_status = HealthStatus.DEGRADED
        elif status_counts[HealthStatus.HEALTHY] > 0:
            overall_status = HealthStatus.HEALTHY
        else:
            overall_status = HealthStatus.UNKNOWN

        return {
            'status': overall_status.value,
            'message': self._get_status_message(overall_status, status_counts),
            'scraper_count': len(self._metrics),
            'healthy_count': status_counts[HealthStatus.HEALTHY],
            'degraded_count': status_counts[HealthStatus.DEGRADED],
            'unhealthy_count': status_counts[HealthStatus.UNHEALTHY],
            'critical_count': status_counts[HealthStatus.CRITICAL],
            'unknown_count': status_counts[HealthStatus.UNKNOWN],
            'total_requests': total_requests,
            'total_successful': total_successful,
            'overall_success_rate': total_successful / total_requests if total_requests > 0 else 0,
            'total_records': total_records,
            'checked_at': datetime.now().isoformat(),
        }

    def reset_metrics(self, scraper_id: str = None):
        """
        Reset metrics for a scraper or all scrapers.

        Args:
            scraper_id: Optional specific scraper (None for all)
        """
        if scraper_id:
            if scraper_id in self._metrics:
                state_code = self._metrics[scraper_id].state_code
                self._metrics[scraper_id] = ScraperMetrics(
                    scraper_id=scraper_id,
                    state_code=state_code
                )
                self._error_counts[scraper_id].clear()
        else:
            self._metrics.clear()
            self._error_counts.clear()
            self._health_history.clear()

    def _classify_error(self, error_message: str) -> str:
        """Classify error message into a category"""
        if not error_message:
            return "unknown"

        error_lower = error_message.lower()

        if "timeout" in error_lower or "timed out" in error_lower:
            return "timeout"
        elif "connection" in error_lower or "network" in error_lower:
            return "connection"
        elif "rate limit" in error_lower or "429" in error_lower:
            return "rate_limit"
        elif "auth" in error_lower or "401" in error_lower or "403" in error_lower:
            return "authentication"
        elif "not found" in error_lower or "404" in error_lower:
            return "not_found"
        elif "500" in error_lower or "server error" in error_lower:
            return "server_error"
        elif "parse" in error_lower or "json" in error_lower:
            return "parse_error"
        else:
            return "other"

    def _status_priority(self, status: HealthStatus) -> int:
        """Get priority for status (higher = worse)"""
        priorities = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.UNKNOWN: 1,
            HealthStatus.DEGRADED: 2,
            HealthStatus.UNHEALTHY: 3,
            HealthStatus.CRITICAL: 4,
        }
        return priorities.get(status, 1)

    def _get_status_message(self, status: HealthStatus,
                           counts: Dict[HealthStatus, int]) -> str:
        """Generate status message"""
        if status == HealthStatus.HEALTHY:
            return "All scrapers operational"
        elif status == HealthStatus.DEGRADED:
            return f"{counts[HealthStatus.DEGRADED]} scraper(s) degraded"
        elif status == HealthStatus.UNHEALTHY:
            return f"{counts[HealthStatus.UNHEALTHY]} scraper(s) unhealthy"
        elif status == HealthStatus.CRITICAL:
            return f"{counts[HealthStatus.CRITICAL]} scraper(s) critical"
        else:
            return "Status unknown"


# Singleton instance
_monitor_instance: Optional[ScraperHealthMonitor] = None


def get_monitor() -> ScraperHealthMonitor:
    """Get the singleton health monitor instance"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = ScraperHealthMonitor()
    return _monitor_instance


def get_scraper_health(scraper_id: str) -> HealthCheckResult:
    """Convenience function to get scraper health"""
    return get_monitor().check_health(scraper_id)


def check_all_scrapers() -> Dict[str, HealthCheckResult]:
    """Convenience function to check all scrapers"""
    return get_monitor().check_all_scrapers()
