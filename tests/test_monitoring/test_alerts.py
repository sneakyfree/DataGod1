"""
Comprehensive tests for the Alert Manager.

Tests cover:
- AlertSeverity enum
- AlertStatus enum
- ComparisonOperator enum
- Alert dataclass
- AlertRule dataclass
- NotificationChannels
- AlertManager class
- Convenience functions
"""

import pytest
from datetime import datetime, timedelta
from datagod.monitoring.alerts import (
    AlertSeverity,
    AlertStatus,
    ComparisonOperator,
    Alert,
    AlertRule,
    AlertManager,
    LogNotificationChannel,
    WebhookNotificationChannel,
    EmailNotificationChannel,
    get_alert_manager,
    send_alert,
    check_alert_rules,
    DEFAULT_RULES,
)


class TestAlertSeverityEnum:
    """Tests for AlertSeverity enum"""

    def test_all_severities_exist(self):
        """Test that all severities are defined"""
        assert AlertSeverity.INFO is not None
        assert AlertSeverity.WARNING is not None
        assert AlertSeverity.ERROR is not None
        assert AlertSeverity.CRITICAL is not None

    def test_severity_values(self):
        """Test severity string values"""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestAlertStatusEnum:
    """Tests for AlertStatus enum"""

    def test_all_statuses_exist(self):
        """Test that all statuses are defined"""
        assert AlertStatus.ACTIVE is not None
        assert AlertStatus.ACKNOWLEDGED is not None
        assert AlertStatus.RESOLVED is not None
        assert AlertStatus.SILENCED is not None

    def test_status_values(self):
        """Test status string values"""
        assert AlertStatus.ACTIVE.value == "active"
        assert AlertStatus.ACKNOWLEDGED.value == "acknowledged"
        assert AlertStatus.RESOLVED.value == "resolved"
        assert AlertStatus.SILENCED.value == "silenced"


class TestComparisonOperatorEnum:
    """Tests for ComparisonOperator enum"""

    def test_all_operators_exist(self):
        """Test that all operators are defined"""
        assert ComparisonOperator.GREATER_THAN is not None
        assert ComparisonOperator.LESS_THAN is not None
        assert ComparisonOperator.GREATER_EQUAL is not None
        assert ComparisonOperator.LESS_EQUAL is not None
        assert ComparisonOperator.EQUALS is not None
        assert ComparisonOperator.NOT_EQUALS is not None


class TestAlert:
    """Tests for Alert dataclass"""

    def test_create_alert(self):
        """Test creating an alert"""
        alert = Alert(
            alert_id="test-001",
            rule_id="rule-001",
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="This is a test alert"
        )
        assert alert.alert_id == "test-001"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.status == AlertStatus.ACTIVE

    def test_alert_acknowledge(self):
        """Test acknowledging an alert"""
        alert = Alert(
            alert_id="test-001",
            rule_id="rule-001",
            severity=AlertSeverity.WARNING,
            title="Test",
            message="Test"
        )
        alert.acknowledge(user="admin")

        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.acknowledged_by == "admin"
        assert alert.acknowledged_at is not None

    def test_alert_resolve(self):
        """Test resolving an alert"""
        alert = Alert(
            alert_id="test-001",
            rule_id="rule-001",
            severity=AlertSeverity.WARNING,
            title="Test",
            message="Test"
        )
        alert.resolve()

        assert alert.status == AlertStatus.RESOLVED
        assert alert.resolved_at is not None

    def test_alert_silence(self):
        """Test silencing an alert"""
        alert = Alert(
            alert_id="test-001",
            rule_id="rule-001",
            severity=AlertSeverity.WARNING,
            title="Test",
            message="Test"
        )
        alert.silence()
        assert alert.status == AlertStatus.SILENCED

    def test_alert_to_dict(self):
        """Test converting alert to dictionary"""
        alert = Alert(
            alert_id="test-001",
            rule_id="rule-001",
            severity=AlertSeverity.CRITICAL,
            title="Test Alert",
            message="Critical issue",
            metadata={"value": 100}
        )
        result = alert.to_dict()

        assert result['alert_id'] == "test-001"
        assert result['severity'] == "critical"
        assert result['status'] == "active"
        assert result['metadata'] == {"value": 100}


class TestAlertRule:
    """Tests for AlertRule dataclass"""

    def test_create_rule(self):
        """Test creating an alert rule"""
        rule = AlertRule(
            rule_id="test-rule",
            name="Test Rule",
            description="Test description",
            metric_name="test.metric",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=100.0
        )
        assert rule.rule_id == "test-rule"
        assert rule.enabled is True

    def test_evaluate_greater_than(self):
        """Test greater than evaluation"""
        rule = AlertRule(
            rule_id="test",
            name="Test",
            description="Test",
            metric_name="test",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=100.0
        )
        assert rule.evaluate(150.0) is True
        assert rule.evaluate(100.0) is False
        assert rule.evaluate(50.0) is False

    def test_evaluate_less_than(self):
        """Test less than evaluation"""
        rule = AlertRule(
            rule_id="test",
            name="Test",
            description="Test",
            metric_name="test",
            operator=ComparisonOperator.LESS_THAN,
            threshold=100.0
        )
        assert rule.evaluate(50.0) is True
        assert rule.evaluate(100.0) is False
        assert rule.evaluate(150.0) is False

    def test_evaluate_greater_equal(self):
        """Test greater or equal evaluation"""
        rule = AlertRule(
            rule_id="test",
            name="Test",
            description="Test",
            metric_name="test",
            operator=ComparisonOperator.GREATER_EQUAL,
            threshold=100.0
        )
        assert rule.evaluate(150.0) is True
        assert rule.evaluate(100.0) is True
        assert rule.evaluate(50.0) is False

    def test_evaluate_less_equal(self):
        """Test less or equal evaluation"""
        rule = AlertRule(
            rule_id="test",
            name="Test",
            description="Test",
            metric_name="test",
            operator=ComparisonOperator.LESS_EQUAL,
            threshold=100.0
        )
        assert rule.evaluate(50.0) is True
        assert rule.evaluate(100.0) is True
        assert rule.evaluate(150.0) is False

    def test_evaluate_equals(self):
        """Test equals evaluation"""
        rule = AlertRule(
            rule_id="test",
            name="Test",
            description="Test",
            metric_name="test",
            operator=ComparisonOperator.EQUALS,
            threshold=100.0
        )
        assert rule.evaluate(100.0) is True
        assert rule.evaluate(99.0) is False

    def test_evaluate_not_equals(self):
        """Test not equals evaluation"""
        rule = AlertRule(
            rule_id="test",
            name="Test",
            description="Test",
            metric_name="test",
            operator=ComparisonOperator.NOT_EQUALS,
            threshold=100.0
        )
        assert rule.evaluate(50.0) is True
        assert rule.evaluate(100.0) is False

    def test_rule_to_dict(self):
        """Test converting rule to dictionary"""
        rule = AlertRule(
            rule_id="test",
            name="Test Rule",
            description="Description",
            metric_name="test.metric",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=100.0,
            severity=AlertSeverity.WARNING
        )
        result = rule.to_dict()

        assert result['rule_id'] == "test"
        assert result['operator'] == "gt"
        assert result['severity'] == "warning"


class TestNotificationChannels:
    """Tests for notification channels"""

    def test_log_channel(self):
        """Test log notification channel"""
        channel = LogNotificationChannel()
        alert = Alert(
            alert_id="test",
            rule_id="test",
            severity=AlertSeverity.WARNING,
            title="Test",
            message="Test message"
        )
        result = channel.send(alert)
        assert result is True

    def test_webhook_channel_creation(self):
        """Test webhook channel creation"""
        channel = WebhookNotificationChannel(
            webhook_url="https://example.com/webhook",
            headers={"Authorization": "Bearer token"}
        )
        assert channel.webhook_url == "https://example.com/webhook"

    def test_email_channel_creation(self):
        """Test email channel creation"""
        channel = EmailNotificationChannel(
            smtp_host="smtp.example.com",
            smtp_port=587,
            from_email="alerts@example.com",
            to_emails=["admin@example.com"],
            username="user",
            password="pass"
        )
        assert channel.smtp_host == "smtp.example.com"


class TestAlertManager:
    """Tests for AlertManager class"""

    @pytest.fixture
    def manager(self):
        """Create fresh manager instance"""
        m = AlertManager()
        m.clear_all()
        return m

    def test_manager_initialization(self, manager):
        """Test manager initialization"""
        assert len(manager._rules) == 0
        assert len(manager._alerts) == 0

    def test_add_rule(self, manager):
        """Test adding a rule"""
        rule = AlertRule(
            rule_id="test",
            name="Test Rule",
            description="Test",
            metric_name="test.metric",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=100.0
        )
        manager.add_rule(rule)
        assert manager.get_rule("test") is not None

    def test_remove_rule(self, manager):
        """Test removing a rule"""
        rule = AlertRule(
            rule_id="test",
            name="Test",
            description="Test",
            metric_name="test",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=100.0
        )
        manager.add_rule(rule)
        manager.remove_rule("test")
        assert manager.get_rule("test") is None

    def test_get_all_rules(self, manager):
        """Test getting all rules"""
        for i in range(3):
            rule = AlertRule(
                rule_id=f"rule-{i}",
                name=f"Rule {i}",
                description="Test",
                metric_name="test",
                operator=ComparisonOperator.GREATER_THAN,
                threshold=100.0
            )
            manager.add_rule(rule)

        rules = manager.get_all_rules()
        assert len(rules) == 3

    def test_add_channel(self, manager):
        """Test adding a notification channel"""
        channel = LogNotificationChannel()
        manager.add_channel(channel)
        assert len(manager._channels) >= 2  # Default + added

    def test_evaluate_triggers_alert(self, manager):
        """Test evaluating a metric triggers alert"""
        rule = AlertRule(
            rule_id="test-rule",
            name="High Value Alert",
            description="Value exceeds threshold",
            metric_name="test.value",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=100.0,
            severity=AlertSeverity.WARNING
        )
        manager.add_rule(rule)

        alerts = manager.evaluate("test.value", 150.0)
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.WARNING

    def test_evaluate_no_trigger(self, manager):
        """Test evaluating a metric doesn't trigger when below threshold"""
        rule = AlertRule(
            rule_id="test-rule",
            name="Test",
            description="Test",
            metric_name="test.value",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=100.0
        )
        manager.add_rule(rule)

        alerts = manager.evaluate("test.value", 50.0)
        assert len(alerts) == 0

    def test_evaluate_disabled_rule(self, manager):
        """Test disabled rule doesn't trigger"""
        rule = AlertRule(
            rule_id="test-rule",
            name="Test",
            description="Test",
            metric_name="test.value",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=100.0,
            enabled=False
        )
        manager.add_rule(rule)

        alerts = manager.evaluate("test.value", 150.0)
        assert len(alerts) == 0

    def test_evaluate_wrong_metric(self, manager):
        """Test wrong metric name doesn't trigger"""
        rule = AlertRule(
            rule_id="test-rule",
            name="Test",
            description="Test",
            metric_name="test.value",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=100.0
        )
        manager.add_rule(rule)

        alerts = manager.evaluate("other.value", 150.0)
        assert len(alerts) == 0

    def test_evaluate_with_tags_filter(self, manager):
        """Test evaluation with tags filter"""
        rule = AlertRule(
            rule_id="test-rule",
            name="Test",
            description="Test",
            metric_name="test.value",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=100.0,
            tags_filter={"env": "prod"}
        )
        manager.add_rule(rule)

        # Should trigger (tags match)
        alerts = manager.evaluate("test.value", 150.0, {"env": "prod"})
        assert len(alerts) == 1

        # Should not trigger (tags don't match)
        alerts = manager.evaluate("test.value", 150.0, {"env": "dev"})
        assert len(alerts) == 0

    def test_evaluate_cooldown(self, manager):
        """Test cooldown prevents duplicate alerts"""
        rule = AlertRule(
            rule_id="test-rule",
            name="Test",
            description="Test",
            metric_name="test.value",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=100.0,
            cooldown_minutes=5
        )
        manager.add_rule(rule)

        # First trigger
        alerts1 = manager.evaluate("test.value", 150.0)
        assert len(alerts1) == 1

        # Second trigger (within cooldown)
        alerts2 = manager.evaluate("test.value", 160.0)
        assert len(alerts2) == 0

    def test_get_alert(self, manager):
        """Test getting an alert by ID"""
        rule = AlertRule(
            rule_id="test-rule",
            name="Test",
            description="Test",
            metric_name="test",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=100.0
        )
        manager.add_rule(rule)
        alerts = manager.evaluate("test", 150.0)

        alert = manager.get_alert(alerts[0].alert_id)
        assert alert is not None

    def test_get_active_alerts(self, manager):
        """Test getting active alerts"""
        rule = AlertRule(
            rule_id="test-rule",
            name="Test",
            description="Test",
            metric_name="test",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=100.0,
            cooldown_minutes=0
        )
        manager.add_rule(rule)

        manager.evaluate("test", 150.0)
        manager.evaluate("test", 160.0)

        active = manager.get_active_alerts()
        assert len(active) >= 1

    def test_get_alerts_by_severity(self, manager):
        """Test getting alerts by severity"""
        rule = AlertRule(
            rule_id="test-rule",
            name="Test",
            description="Test",
            metric_name="test",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=100.0,
            severity=AlertSeverity.CRITICAL
        )
        manager.add_rule(rule)
        manager.evaluate("test", 150.0)

        critical = manager.get_alerts_by_severity(AlertSeverity.CRITICAL)
        warning = manager.get_alerts_by_severity(AlertSeverity.WARNING)

        assert len(critical) >= 1
        assert len(warning) == 0

    def test_acknowledge_alert(self, manager):
        """Test acknowledging an alert"""
        rule = AlertRule(
            rule_id="test",
            name="Test",
            description="Test",
            metric_name="test",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=100.0
        )
        manager.add_rule(rule)
        alerts = manager.evaluate("test", 150.0)

        result = manager.acknowledge_alert(alerts[0].alert_id, "admin")
        assert result is True

        alert = manager.get_alert(alerts[0].alert_id)
        assert alert.status == AlertStatus.ACKNOWLEDGED

    def test_resolve_alert(self, manager):
        """Test resolving an alert"""
        rule = AlertRule(
            rule_id="test",
            name="Test",
            description="Test",
            metric_name="test",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=100.0
        )
        manager.add_rule(rule)
        alerts = manager.evaluate("test", 150.0)

        result = manager.resolve_alert(alerts[0].alert_id)
        assert result is True

        alert = manager.get_alert(alerts[0].alert_id)
        assert alert.status == AlertStatus.RESOLVED

    def test_silence_alert(self, manager):
        """Test silencing an alert"""
        rule = AlertRule(
            rule_id="test",
            name="Test",
            description="Test",
            metric_name="test",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=100.0
        )
        manager.add_rule(rule)
        alerts = manager.evaluate("test", 150.0)

        result = manager.silence_alert(alerts[0].alert_id)
        assert result is True

    def test_get_alert_summary(self, manager):
        """Test getting alert summary"""
        rule = AlertRule(
            rule_id="test",
            name="Test",
            description="Test",
            metric_name="test",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=100.0
        )
        manager.add_rule(rule)
        manager.evaluate("test", 150.0)

        summary = manager.get_alert_summary()
        assert 'total_alerts' in summary
        assert 'active_alerts' in summary
        assert 'by_status' in summary
        assert 'by_severity' in summary

    def test_cleanup_old_alerts(self, manager):
        """Test cleaning up old alerts"""
        rule = AlertRule(
            rule_id="test",
            name="Test",
            description="Test",
            metric_name="test",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=100.0
        )
        manager.add_rule(rule)
        alerts = manager.evaluate("test", 150.0)

        # Resolve the alert
        manager.resolve_alert(alerts[0].alert_id)

        # Manually set old timestamp
        manager._alerts[alerts[0].alert_id].created_at = datetime.now() - timedelta(days=60)

        manager.cleanup_old_alerts(days=30)
        assert manager.get_alert(alerts[0].alert_id) is None


class TestDefaultRules:
    """Tests for default alert rules"""

    def test_default_rules_exist(self):
        """Test that default rules are defined"""
        assert len(DEFAULT_RULES) >= 5

    def test_default_rules_have_required_fields(self):
        """Test default rules have required fields"""
        for rule in DEFAULT_RULES:
            assert rule.rule_id is not None
            assert rule.name is not None
            assert rule.metric_name is not None
            assert rule.threshold is not None


class TestConvenienceFunctions:
    """Tests for convenience functions"""

    def test_get_alert_manager(self):
        """Test getting singleton manager"""
        manager1 = get_alert_manager()
        manager2 = get_alert_manager()
        assert manager1 is manager2

    def test_send_alert(self):
        """Test convenience send alert function"""
        alert = send_alert(
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="Test message",
            metadata={"key": "value"}
        )
        assert isinstance(alert, Alert)
        assert alert.severity == AlertSeverity.WARNING
        assert alert.rule_id == "manual"

    def test_check_alert_rules(self):
        """Test convenience check rules function"""
        manager = get_alert_manager()

        # The default rules are already loaded
        # Check against the failure rate rule
        alerts = check_alert_rules("scraper.failure_rate", 0.6)
        assert isinstance(alerts, list)
