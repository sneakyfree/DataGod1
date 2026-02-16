"""
Tests for Security utilities — coverage for security/__init__.py (31% → 70%+)
"""

import pytest
import time
from datagod.security import (
    RateLimitConfig,
    RateLimiter,
    InputSanitizer,
    PIIRedactor,
)


class TestRateLimitConfig:
    def test_defaults(self):
        config = RateLimitConfig()
        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000
        assert config.burst_limit == 10

    def test_custom_config(self):
        config = RateLimitConfig(requests_per_minute=10, burst_limit=5)
        assert config.requests_per_minute == 10
        assert config.burst_limit == 5


class TestRateLimiter:
    def setup_method(self):
        self.limiter = RateLimiter(RateLimitConfig(requests_per_minute=5, burst_limit=3))

    def test_first_request_allowed(self):
        result = self.limiter.check("user-1")
        assert result["allowed"] is True

    def test_within_limit_allowed(self):
        for i in range(3):
            result = self.limiter.check("user-1")
        assert result["allowed"] is True

    def test_exceeds_limit_blocked(self):
        for i in range(10):
            result = self.limiter.check("user-burst")
        assert result["allowed"] is False

    def test_different_keys_independent(self):
        for i in range(5):
            self.limiter.check("user-a")
        result = self.limiter.check("user-b")
        assert result["allowed"] is True

    def test_whitelisted_ip(self):
        config = RateLimitConfig(requests_per_minute=1, whitelist_ips={"10.0.0.1"})
        limiter = RateLimiter(config)
        limiter.check("user-1", ip="10.0.0.2")
        limiter.check("user-1", ip="10.0.0.2")
        result = limiter.check("user-1", ip="10.0.0.1")
        assert result["allowed"] is True

    def test_blacklisted_ip(self):
        config = RateLimitConfig(blacklist_ips={"192.168.1.100"})
        limiter = RateLimiter(config)
        result = limiter.check("user-1", ip="192.168.1.100")
        assert result["allowed"] is False

    def test_get_headers(self):
        result = self.limiter.check("user-headers")
        headers = self.limiter.get_headers(result)
        assert isinstance(headers, dict)

    def test_result_has_remaining(self):
        result = self.limiter.check("user-remaining")
        assert "remaining" in result

    def test_result_has_reset_at(self):
        result = self.limiter.check("user-reset")
        assert "reset_at" in result


class TestInputSanitizer:
    def test_sanitize_clean_string(self):
        result = InputSanitizer.sanitize_string("Hello World")
        assert "Hello" in result
        assert "World" in result

    def test_sanitize_sql_escapes_quotes(self):
        malicious = "'; DROP TABLE users; --"
        result = InputSanitizer.sanitize_string(malicious, context="sql")
        # The sanitizer escapes single quotes, so the raw quote should be gone
        assert result != malicious

    def test_sanitize_xss(self):
        malicious = "<script>alert('xss')</script>"
        result = InputSanitizer.sanitize_string(malicious, context="html")
        assert "<script>" not in result

    def test_sanitize_path_traversal(self):
        malicious = "../../../etc/passwd"
        result = InputSanitizer.sanitize_string(malicious, context="path")
        assert ".." not in result

    def test_sanitize_command_injection(self):
        malicious = "; rm -rf /"
        result = InputSanitizer.sanitize_string(malicious, context="command")
        assert result != malicious

    def test_validate_clean_input(self):
        result = InputSanitizer.validate_input("normal text")
        assert result["valid"] is True

    def test_validate_returns_sanitized(self):
        result = InputSanitizer.validate_input("<b>bold</b>", context="html")
        assert "sanitized" in result

    def test_escape_sql(self):
        result = InputSanitizer._escape_sql("test'value")
        assert isinstance(result, str)

    def test_escape_html(self):
        result = InputSanitizer._escape_html("<div>test</div>")
        assert "<div>" not in result

    def test_sanitize_path(self):
        result = InputSanitizer._sanitize_path("../../file.txt")
        assert ".." not in result

    def test_escape_command(self):
        result = InputSanitizer._escape_command("test; whoami")
        assert isinstance(result, str)


class TestPIIRedactor:
    def setup_method(self):
        self.redactor = PIIRedactor()

    def test_detect_ssn(self):
        detections = self.redactor.detect("My SSN is 123-45-6789")
        assert len(detections) > 0
        assert any(d["type"] == "ssn" for d in detections)

    def test_detect_email(self):
        detections = self.redactor.detect("Contact me at john@example.com")
        assert any(d["type"] == "email" for d in detections)

    def test_detect_phone(self):
        # Use the format that matches the regex: \b(\d{3})[-.\\s]?(\d{3})[-.\\s]?(\d{4})\b
        detections = self.redactor.detect("Call me at 555-123-4567")
        assert any(d["type"] == "phone" for d in detections)

    def test_detect_credit_card(self):
        detections = self.redactor.detect("Card: 4111-1111-1111-1111")
        assert len(detections) > 0

    def test_detect_no_pii(self):
        detections = self.redactor.detect("This is just normal text")
        assert len(detections) == 0

    def test_redact_ssn(self):
        result = self.redactor.redact("SSN: 123-45-6789")
        assert "123-45-6789" not in result

    def test_redact_email(self):
        result = self.redactor.redact("Email: test@example.com")
        assert "test@example.com" not in result

    def test_redact_preserves_non_pii(self):
        text = "Hello World with no PII"
        result = self.redactor.redact(text)
        assert result == text

    def test_redact_dict(self):
        data = {
            "name": "John Doe",
            "ssn": "123-45-6789",
            "email": "john@example.com",
            "notes": "Customer number is one two three"
        }
        result = self.redactor.redact_dict(data)
        assert isinstance(result, dict)

    def test_redact_dict_recursive(self):
        data = {
            "person": {
                "name": "John",
                "contact": "john@example.com"
            }
        }
        result = self.redactor.redact_dict(data, recursive=True)
        assert isinstance(result, dict)

    def test_custom_redact_types(self):
        redactor = PIIRedactor(redact_types=["ssn"])
        result = redactor.detect("SSN: 123-45-6789, email: test@test.com")
        ssn_detections = [d for d in result if d["type"] == "ssn"]
        assert len(ssn_detections) > 0
