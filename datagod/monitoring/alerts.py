"""
Alert Manager

Configurable alerting system for monitoring.

Features:
- Alert rules and thresholds
- Multiple notification channels
- Alert history and deduplication
- Escalation policies
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status"""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SILENCED = "silenced"


class ComparisonOperator(Enum):
    """Comparison operators for alert rules"""

    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_EQUAL = "gte"
    LESS_EQUAL = "lte"
    EQUALS = "eq"
    NOT_EQUALS = "neq"


@dataclass
class Alert:
    """Represents an alert"""

    alert_id: str
    rule_id: str
    severity: AlertSeverity
    title: str
    message: str
    status: AlertStatus = AlertStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    notification_sent: bool = False

    def acknowledge(self, user: str = None):
        """Acknowledge the alert"""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.now()
        self.acknowledged_by = user
        self.updated_at = datetime.now()

    def resolve(self):
        """Resolve the alert"""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.now()
        self.updated_at = datetime.now()

    def silence(self):
        """Silence the alert"""
        self.status = AlertStatus.SILENCED
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "acknowledged_at": (
                self.acknowledged_at.isoformat() if self.acknowledged_at else None
            ),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "acknowledged_by": self.acknowledged_by,
            "metadata": self.metadata,
            "notification_sent": self.notification_sent,
        }


@dataclass
class AlertRule:
    """Defines when to trigger an alert"""

    rule_id: str
    name: str
    description: str
    metric_name: str
    operator: ComparisonOperator
    threshold: float
    severity: AlertSeverity = AlertSeverity.WARNING
    tags_filter: Dict[str, str] = field(default_factory=dict)
    cooldown_minutes: int = 5  # Minimum time between alerts
    enabled: bool = True

    def evaluate(self, value: float) -> bool:
        """Evaluate if the rule is triggered"""
        if self.operator == ComparisonOperator.GREATER_THAN:
            return value > self.threshold
        elif self.operator == ComparisonOperator.LESS_THAN:
            return value < self.threshold
        elif self.operator == ComparisonOperator.GREATER_EQUAL:
            return value >= self.threshold
        elif self.operator == ComparisonOperator.LESS_EQUAL:
            return value <= self.threshold
        elif self.operator == ComparisonOperator.EQUALS:
            return value == self.threshold
        elif self.operator == ComparisonOperator.NOT_EQUALS:
            return value != self.threshold
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "metric_name": self.metric_name,
            "operator": self.operator.value,
            "threshold": self.threshold,
            "severity": self.severity.value,
            "tags_filter": self.tags_filter,
            "cooldown_minutes": self.cooldown_minutes,
            "enabled": self.enabled,
        }


class NotificationChannel:
    """Base class for notification channels"""

    def send(self, alert: Alert) -> bool:
        """Send notification for an alert"""
        raise NotImplementedError


class LogNotificationChannel(NotificationChannel):
    """Notification channel that logs alerts"""

    def send(self, alert: Alert) -> bool:
        """Log the alert"""
        log_method = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.ERROR: logger.error,
            AlertSeverity.CRITICAL: logger.critical,
        }.get(alert.severity, logger.warning)

        log_method(
            f"ALERT [{alert.severity.value.upper()}]: {alert.title} - {alert.message}"
        )
        return True


class WebhookNotificationChannel(NotificationChannel):
    """Notification channel that sends webhooks"""

    def __init__(self, webhook_url: str, headers: Dict[str, str] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {"Content-Type": "application/json"}

    def send(self, alert: Alert) -> bool:
        """Send webhook notification"""
        try:
            import urllib.error
            import urllib.request

            payload = json.dumps(alert.to_dict()).encode("utf-8")
            request = urllib.request.Request(
                self.webhook_url, data=payload, headers=self.headers, method="POST"
            )

            with urllib.request.urlopen(
                request, timeout=10
            ) as response:  # nosec B310 - internal alert webhook URL only
                return response.status == 200

        except Exception as e:
            logger.error(f"Failed to send webhook: {e}")
            return False


class EmailNotificationChannel(NotificationChannel):
    """Notification channel that sends emails"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        from_email: str,
        to_emails: List[str],
        username: str = None,
        password: str = None,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_email = from_email
        self.to_emails = to_emails
        self.username = username
        self.password = password

    def send(self, alert: Alert) -> bool:
        """Send email notification"""
        try:
            import smtplib
            from email.mime.text import MIMEText

            subject = f"[{alert.severity.value.upper()}] {alert.title}"
            body = f"""
Alert: {alert.title}
Severity: {alert.severity.value}
Status: {alert.status.value}
Time: {alert.created_at.isoformat()}

Message:
{alert.message}

Metadata:
{json.dumps(alert.metadata, indent=2)}
            """

            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = ", ".join(self.to_emails)

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.username and self.password:
                    server.starttls()
                    server.login(self.username, self.password)
                server.sendmail(self.from_email, self.to_emails, msg.as_string())

            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False


class AlertManager:
    """
    Manages alerts and notifications.

    Features:
    - Register alert rules
    - Evaluate metrics against rules
    - Send notifications
    - Track alert history
    """

    def __init__(self):
        """Initialize the alert manager"""
        self._rules: Dict[str, AlertRule] = {}
        self._alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        self._channels: List[NotificationChannel] = [LogNotificationChannel()]
        self._last_alert_times: Dict[str, datetime] = {}
        self._alert_counter = 0

    def add_rule(self, rule: AlertRule):
        """Add an alert rule"""
        self._rules[rule.rule_id] = rule
        logger.info(f"Added alert rule: {rule.name}")

    def remove_rule(self, rule_id: str):
        """Remove an alert rule"""
        if rule_id in self._rules:
            del self._rules[rule_id]
            logger.info(f"Removed alert rule: {rule_id}")

    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """Get an alert rule by ID"""
        return self._rules.get(rule_id)

    def get_all_rules(self) -> List[AlertRule]:
        """Get all alert rules"""
        return list(self._rules.values())

    def add_channel(self, channel: NotificationChannel):
        """Add a notification channel"""
        self._channels.append(channel)

    def evaluate(
        self, metric_name: str, value: float, tags: Dict[str, str] = None
    ) -> List[Alert]:
        """
        Evaluate a metric against all applicable rules.

        Args:
            metric_name: Name of the metric
            value: Metric value
            tags: Optional tags

        Returns:
            List of triggered alerts
        """
        tags = tags or {}
        triggered_alerts = []

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            if rule.metric_name != metric_name:
                continue

            # Check tags filter
            if rule.tags_filter:
                if not all(tags.get(k) == v for k, v in rule.tags_filter.items()):
                    continue

            # Check cooldown
            last_alert = self._last_alert_times.get(rule.rule_id)
            if last_alert:
                cooldown = timedelta(minutes=rule.cooldown_minutes)
                if datetime.now() - last_alert < cooldown:
                    continue

            # Evaluate rule
            if rule.evaluate(value):
                alert = self._create_alert(rule, value, tags)
                triggered_alerts.append(alert)
                self._last_alert_times[rule.rule_id] = datetime.now()

        return triggered_alerts

    def _create_alert(
        self, rule: AlertRule, value: float, tags: Dict[str, str]
    ) -> Alert:
        """Create an alert from a triggered rule"""
        self._alert_counter += 1
        alert_id = (
            f"alert-{self._alert_counter}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )

        alert = Alert(
            alert_id=alert_id,
            rule_id=rule.rule_id,
            severity=rule.severity,
            title=rule.name,
            message=f"{rule.description}. Current value: {value}, Threshold: {rule.threshold}",
            metadata={
                "metric_name": rule.metric_name,
                "value": value,
                "threshold": rule.threshold,
                "operator": rule.operator.value,
                "tags": tags,
            },
        )

        self._alerts[alert_id] = alert
        self._alert_history.append(alert)

        # Send notifications
        self._send_notifications(alert)

        return alert

    def _send_notifications(self, alert: Alert):
        """Send notifications for an alert"""
        for channel in self._channels:
            try:
                if channel.send(alert):
                    alert.notification_sent = True
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get an alert by ID"""
        return self._alerts.get(alert_id)

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return [a for a in self._alerts.values() if a.status == AlertStatus.ACTIVE]

    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        """Get alerts by severity"""
        return [a for a in self._alerts.values() if a.severity == severity]

    def acknowledge_alert(self, alert_id: str, user: str = None) -> bool:
        """Acknowledge an alert"""
        alert = self._alerts.get(alert_id)
        if alert:
            alert.acknowledge(user)
            return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        alert = self._alerts.get(alert_id)
        if alert:
            alert.resolve()
            return True
        return False

    def silence_alert(self, alert_id: str) -> bool:
        """Silence an alert"""
        alert = self._alerts.get(alert_id)
        if alert:
            alert.silence()
            return True
        return False

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of all alerts"""
        status_counts = {}
        severity_counts = {}

        for alert in self._alerts.values():
            status_counts[alert.status.value] = (
                status_counts.get(alert.status.value, 0) + 1
            )
            severity_counts[alert.severity.value] = (
                severity_counts.get(alert.severity.value, 0) + 1
            )

        return {
            "total_alerts": len(self._alerts),
            "active_alerts": len(self.get_active_alerts()),
            "by_status": status_counts,
            "by_severity": severity_counts,
            "rules_count": len(self._rules),
            "channels_count": len(self._channels),
        }

    def cleanup_old_alerts(self, days: int = 30):
        """Remove alerts older than specified days"""
        cutoff = datetime.now() - timedelta(days=days)
        old_alerts = [
            a.alert_id
            for a in self._alerts.values()
            if a.created_at < cutoff
            and a.status in (AlertStatus.RESOLVED, AlertStatus.SILENCED)
        ]

        for alert_id in old_alerts:
            del self._alerts[alert_id]

        logger.info(f"Cleaned up {len(old_alerts)} old alerts")

    def clear_all(self):
        """Clear all alerts and rules"""
        self._rules.clear()
        self._alerts.clear()
        self._alert_history.clear()
        self._last_alert_times.clear()


# Default alert rules
DEFAULT_RULES = [
    AlertRule(
        rule_id="scraper-failure-rate-high",
        name="High Scraper Failure Rate",
        description="Scraper failure rate exceeds 25%",
        metric_name="scraper.failure_rate",
        operator=ComparisonOperator.GREATER_THAN,
        threshold=0.25,
        severity=AlertSeverity.WARNING,
    ),
    AlertRule(
        rule_id="scraper-failure-rate-critical",
        name="Critical Scraper Failure Rate",
        description="Scraper failure rate exceeds 50%",
        metric_name="scraper.failure_rate",
        operator=ComparisonOperator.GREATER_THAN,
        threshold=0.50,
        severity=AlertSeverity.CRITICAL,
    ),
    AlertRule(
        rule_id="api-quota-warning",
        name="API Quota Warning",
        description="API quota usage exceeds 75%",
        metric_name="api.quota_usage_percent",
        operator=ComparisonOperator.GREATER_THAN,
        threshold=75.0,
        severity=AlertSeverity.WARNING,
    ),
    AlertRule(
        rule_id="api-quota-critical",
        name="API Quota Critical",
        description="API quota usage exceeds 90%",
        metric_name="api.quota_usage_percent",
        operator=ComparisonOperator.GREATER_THAN,
        threshold=90.0,
        severity=AlertSeverity.CRITICAL,
    ),
    AlertRule(
        rule_id="response-time-slow",
        name="Slow Response Time",
        description="Average response time exceeds 5 seconds",
        metric_name="scraper.response_time_ms",
        operator=ComparisonOperator.GREATER_THAN,
        threshold=5000.0,
        severity=AlertSeverity.WARNING,
    ),
    AlertRule(
        rule_id="data-freshness-stale",
        name="Stale Data Warning",
        description="Data has not been updated in 24 hours",
        metric_name="data.freshness_hours",
        operator=ComparisonOperator.GREATER_THAN,
        threshold=24.0,
        severity=AlertSeverity.WARNING,
    ),
]


# Singleton instance
_manager_instance: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get the singleton alert manager"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = AlertManager()
        # Add default rules
        for rule in DEFAULT_RULES:
            _manager_instance.add_rule(rule)
    return _manager_instance


def send_alert(
    severity: AlertSeverity, title: str, message: str, metadata: Dict[str, Any] = None
) -> Alert:
    """Convenience function to send a manual alert"""
    manager = get_alert_manager()
    manager._alert_counter += 1
    alert_id = (
        f"manual-{manager._alert_counter}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )

    alert = Alert(
        alert_id=alert_id,
        rule_id="manual",
        severity=severity,
        title=title,
        message=message,
        metadata=metadata or {},
    )

    manager._alerts[alert_id] = alert
    manager._alert_history.append(alert)
    manager._send_notifications(alert)

    return alert


def check_alert_rules(
    metric_name: str, value: float, tags: Dict[str, str] = None
) -> List[Alert]:
    """Convenience function to check alert rules"""
    return get_alert_manager().evaluate(metric_name, value, tags)
