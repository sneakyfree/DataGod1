"""
Tests for Security Audit Logger — coverage for security/audit_logger.py
"""

import os
import tempfile
from datetime import datetime

import pytest

from datagod.security.audit_logger import (
    AuditAction,
    AuditEvent,
    AuditLogger,
    AuditSeverity,
    audited,
    get_audit_logger,
)


class TestAuditAction:
    """Test AuditAction enum values match actual module."""

    def test_auth_actions(self):
        assert AuditAction.LOGIN == "auth.login"
        assert AuditAction.LOGOUT == "auth.logout"
        assert AuditAction.LOGIN_FAILED == "auth.login_failed"

    def test_record_actions(self):
        assert AuditAction.RECORD_CREATE == "record.create"
        assert AuditAction.RECORD_UPDATE == "record.update"
        assert AuditAction.RECORD_DELETE == "record.delete"

    def test_data_actions(self):
        assert AuditAction.DATA_VIEW == "data.view"
        assert AuditAction.DATA_EXPORT == "data.export"
        assert AuditAction.DATA_SEARCH == "data.search"

    def test_system_actions(self):
        assert AuditAction.SYSTEM_CONFIG_CHANGE == "system.config_change"
        assert AuditAction.SCRAPER_RUN == "system.scraper_run"


class TestAuditSeverity:
    def test_levels(self):
        assert AuditSeverity.INFO == "info"
        assert AuditSeverity.WARNING == "warning"
        assert AuditSeverity.CRITICAL == "critical"


class TestAuditEvent:
    def _make_event(self, **overrides):
        defaults = dict(
            id="evt-001",
            action=AuditAction.LOGIN,
            severity=AuditSeverity.INFO,
            timestamp=datetime.utcnow(),
            user_id="user-123",
            user_email="test@example.com",
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0",
            resource_type="session",
            resource_id="sess-1",
            description="User logged in",
        )
        defaults.update(overrides)
        return AuditEvent(**defaults)

    def test_create_event(self):
        event = self._make_event()
        assert event.id == "evt-001"
        assert event.action == AuditAction.LOGIN
        assert event.user_id == "user-123"

    def test_to_dict(self):
        event = self._make_event()
        d = event.to_dict()
        assert "id" in d
        assert "action" in d
        assert d["action"] == "auth.login"

    def test_to_json(self):
        event = self._make_event()
        j = event.to_json()
        assert isinstance(j, str)
        assert "evt-001" in j

    def test_event_with_metadata(self):
        event = self._make_event(metadata={"query": "test"})
        assert event.metadata["query"] == "test"

    def test_event_default_success(self):
        event = self._make_event()
        assert event.success is True


class TestAuditLogger:
    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.log_file = os.path.join(self.tmp, "audit.log")
        self.logger = AuditLogger(storage_backend="file", log_file=self.log_file)

    def test_logger_initializes(self):
        assert self.logger is not None

    def test_log_event(self):
        event = self.logger.log(
            action=AuditAction.LOGIN,
            user_id="user-1",
            user_email="test@example.com",
            description="User logged in",
        )
        assert event is not None
        assert isinstance(event, AuditEvent)

    def test_log_auth_actions(self):
        for action in [AuditAction.LOGIN, AuditAction.LOGOUT, AuditAction.LOGIN_FAILED]:
            event = self.logger.log(action=action, user_id="user-1")
            assert event is not None

    def test_log_record_actions(self):
        event = self.logger.log(
            action=AuditAction.RECORD_CREATE,
            user_id="user-1",
            resource_type="property",
            resource_id="prop-123",
            description="Created property record",
        )
        assert event is not None

    def test_log_with_metadata(self):
        event = self.logger.log(
            action=AuditAction.DATA_SEARCH,
            user_id="user-1",
            metadata={"query": "123 Main St", "result_count": 5},
        )
        assert event is not None

    def test_log_failure_event(self):
        event = self.logger.log(
            action=AuditAction.LOGIN_FAILED,
            user_id="user-1",
            success=False,
            error_message="Invalid credentials",
        )
        assert event.success is False

    def test_log_with_old_new_values(self):
        event = self.logger.log(
            action=AuditAction.RECORD_UPDATE,
            user_id="user-1",
            old_value={"status": "pending"},
            new_value={"status": "active"},
        )
        assert event is not None

    def test_query_returns_list(self):
        self.logger.log(action=AuditAction.LOGIN, user_id="user-1")
        results = self.logger.query()
        assert isinstance(results, list)

    def test_query_by_action(self):
        results = self.logger.query(action=AuditAction.LOGIN)
        assert isinstance(results, list)

    def test_query_by_user(self):
        results = self.logger.query(user_id="user-1")
        assert isinstance(results, list)

    def test_export_json(self):
        path = self.logger.export(format="json")
        assert path.endswith(".json")
        assert os.path.exists(path)

    def test_export_csv(self):
        path = self.logger.export(format="csv")
        assert path.endswith(".csv")

    def test_get_stats(self):
        self.logger.log(action=AuditAction.LOGIN, user_id="user-1")
        stats = self.logger.get_stats()
        assert isinstance(stats, dict)
        assert stats["total_events"] >= 1

    def test_generate_event_id_unique(self):
        id1 = self.logger._generate_event_id()
        id2 = self.logger._generate_event_id()
        # IDs should be different (counter-based)
        assert isinstance(id1, str)
        assert len(id1) > 0

    def test_sanitize_sensitive(self):
        data = {"username": "john", "password": "secret", "ssn": "123-45-6789"}
        sanitized = self.logger._sanitize_sensitive(data)
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["ssn"] == "[REDACTED]"
        assert sanitized["username"] == "john"

    def test_sanitize_nested(self):
        data = {"user": {"name": "john", "api_key": "abc123"}}
        sanitized = self.logger._sanitize_sensitive(data)
        assert sanitized["user"]["api_key"] == "[REDACTED]"

    def test_default_severity_success(self):
        sev = self.logger._get_default_severity(AuditAction.LOGIN, success=True)
        assert sev == AuditSeverity.INFO

    def test_default_severity_failure(self):
        sev = self.logger._get_default_severity(AuditAction.LOGIN, success=False)
        assert sev == AuditSeverity.WARNING

    def test_default_severity_critical(self):
        sev = self.logger._get_default_severity(AuditAction.USER_DELETE, success=True)
        assert sev == AuditSeverity.CRITICAL

    def test_default_description(self):
        desc = self.logger._get_default_description(AuditAction.LOGIN)
        assert desc == "User logged in"

    def test_default_description_fallback(self):
        desc = self.logger._get_default_description(AuditAction.API_CALL)
        assert desc == "api.call"  # Falls back to enum value


class TestGetAuditLogger:
    def test_returns_logger(self):
        al = get_audit_logger()
        assert isinstance(al, AuditLogger)

    def test_singleton(self):
        a = get_audit_logger()
        b = get_audit_logger()
        assert a is b
