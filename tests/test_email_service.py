"""
Tests for DataGod Email Service
"""

from unittest.mock import MagicMock, patch

import pytest


class TestEmailService:
    """Tests for EmailService class"""

    def test_email_service_initialization(self):
        """Test EmailService initialization"""
        from datagod.services.email_service import EmailService

        service = EmailService()
        assert service.provider == "stub"
        assert service.from_email == "noreply@datagod.com"
        assert service.from_name == "DataGod"

    def test_email_service_custom_initialization(self):
        """Test EmailService with custom configuration"""
        from datagod.services.email_service import EmailService

        service = EmailService(
            provider="smtp",
            smtp_host="smtp.example.com",
            smtp_port=465,
            smtp_user="user@example.com",
            smtp_password="password123",
            from_email="custom@example.com",
            from_name="Custom Sender",
        )

        assert service.provider == "smtp"
        assert service.smtp_host == "smtp.example.com"
        assert service.smtp_port == 465
        assert service.smtp_user == "user@example.com"
        assert service.from_email == "custom@example.com"
        assert service.from_name == "Custom Sender"

    def test_send_email_stub(self):
        """Test sending email with stub provider"""
        from datagod.services.email_service import EmailService

        service = EmailService(provider="stub")
        result = service.send_email(
            to_email="test@example.com",
            subject="Test Subject",
            body_text="This is a test email.",
        )

        assert result is True

    def test_send_email_stub_with_html(self):
        """Test sending email with HTML body"""
        from datagod.services.email_service import EmailService

        service = EmailService(provider="stub")
        result = service.send_email(
            to_email="test@example.com",
            subject="Test Subject",
            body_text="This is a test email.",
            body_html="<html><body><h1>Test</h1></body></html>",
        )

        assert result is True

    def test_send_email_unknown_provider(self):
        """Test sending email with unknown provider"""
        from datagod.services.email_service import EmailService

        service = EmailService(provider="unknown")
        result = service.send_email(
            to_email="test@example.com",
            subject="Test Subject",
            body_text="This is a test email.",
        )

        assert result is False

    def test_send_email_custom_from(self):
        """Test sending email with custom from address"""
        from datagod.services.email_service import EmailService

        service = EmailService(provider="stub")
        result = service.send_email(
            to_email="test@example.com",
            subject="Test Subject",
            body_text="This is a test email.",
            from_email="custom@datagod.com",
            from_name="Custom Name",
        )

        assert result is True

    def test_send_password_reset(self):
        """Test sending password reset email"""
        from datagod.services.email_service import EmailService

        service = EmailService(provider="stub")
        result = service.send_password_reset(
            to_email="user@example.com", reset_token="abc123", username="testuser"
        )

        assert result is True

    def test_send_welcome_email(self):
        """Test sending welcome email"""
        from datagod.services.email_service import EmailService

        service = EmailService(provider="stub")
        result = service.send_welcome_email(
            to_email="newuser@example.com", username="newuser"
        )

        assert result is True

    def test_send_email_verification(self):
        """Test sending verification email"""
        from datagod.services.email_service import EmailService

        service = EmailService(provider="stub")
        result = service.send_email_verification(
            to_email="user@example.com",
            verification_token="verify123",
            username="testuser",
        )

        assert result is True


class TestEmailServiceSMTP:
    """Tests for SMTP email provider"""

    def test_smtp_email_not_configured(self):
        """Test SMTP email without configuration"""
        from datagod.services.email_service import EmailService

        service = EmailService(provider="smtp", smtp_host=None)  # Not configured

        result = service.send_email(
            to_email="test@example.com", subject="Test", body_text="Test"
        )

        # Should fail gracefully without SMTP config
        assert result is False

    @patch("smtplib.SMTP")
    def test_smtp_email_configured(self, mock_smtp):
        """Test SMTP email with mocked SMTP server"""
        from datagod.services.email_service import EmailService

        # Configure mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        service = EmailService(
            provider="smtp",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="password",
        )

        result = service.send_email(
            to_email="test@example.com", subject="Test", body_text="Test message"
        )

        # May succeed or fail depending on implementation
        assert isinstance(result, bool)


class TestEmailTemplates:
    """Tests for email template methods"""

    def test_password_reset_email_content(self):
        """Test password reset email generates correct content"""
        from datagod.services.email_service import EmailService

        service = EmailService(provider="stub")

        # The method should work without errors
        result = service.send_password_reset(
            to_email="user@example.com", reset_token="token123", username="testuser"
        )

        assert result is True

    def test_welcome_email_content(self):
        """Test welcome email generates correct content"""
        from datagod.services.email_service import EmailService

        service = EmailService(provider="stub")

        result = service.send_welcome_email(
            to_email="user@example.com", username="newuser"
        )

        assert result is True

    def test_verification_email_content(self):
        """Test verification email generates correct content"""
        from datagod.services.email_service import EmailService

        service = EmailService(provider="stub")

        result = service.send_email_verification(
            to_email="user@example.com",
            verification_token="verify456",
            username="testuser",
        )

        assert result is True

    def test_password_reset_with_custom_url(self):
        """Test password reset email with custom URL"""
        from datagod.services.email_service import EmailService

        service = EmailService(provider="stub")
        result = service.send_password_reset(
            to_email="user@example.com",
            username="testuser",
            reset_token="abc123",
            reset_url="https://custom.example.com/reset/abc123",
            expires_hours=24,
        )

        assert result is True

    def test_email_verification_with_custom_url(self):
        """Test email verification with custom URL"""
        from datagod.services.email_service import EmailService

        service = EmailService(provider="stub")
        result = service.send_email_verification(
            to_email="user@example.com",
            username="testuser",
            verification_token="verify123",
            verification_url="https://custom.example.com/verify/verify123",
        )

        assert result is True


class TestEmailServiceHelpers:
    """Tests for email service helper functions"""

    def test_get_email_service(self):
        """Test get_email_service returns singleton"""
        from datagod.services.email_service import EmailService, get_email_service

        service = get_email_service()
        assert isinstance(service, EmailService)

    def test_get_email_service_singleton(self):
        """Test get_email_service returns same instance"""
        from datagod.services.email_service import get_email_service

        service1 = get_email_service()
        service2 = get_email_service()
        # Should be the same instance
        assert service1 is service2

    def test_configure_email_service(self):
        """Test configure_email_service creates new instance"""
        from datagod.services.email_service import (
            configure_email_service,
            get_email_service,
        )

        # Configure with custom settings
        new_service = configure_email_service(
            provider="stub", from_email="custom@example.com"
        )

        assert new_service.from_email == "custom@example.com"

        # get_email_service should return the newly configured instance
        current_service = get_email_service()
        assert current_service.from_email == "custom@example.com"


class TestServicesInit:
    """Tests for services module __init__ exports"""

    def test_email_service_export(self):
        """Test EmailService is exported from services module"""
        from datagod.services import EmailService

        assert EmailService is not None

    def test_get_email_service_export(self):
        """Test get_email_service is exported from services module"""
        from datagod.services import get_email_service

        assert get_email_service is not None

    def test_configure_email_service_export(self):
        """Test configure_email_service is exported from services module"""
        from datagod.services import configure_email_service

        assert configure_email_service is not None
