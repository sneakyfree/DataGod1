"""
DataGod Email Service

Provides email sending functionality for the DataGod platform.
Currently implements a stub that logs emails; can be extended to use
real email providers (SMTP, SendGrid, SES, etc.).
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailService:
    """
    Email service for sending various types of emails.

    Currently implements a stub that logs emails to console.
    In production, configure with an email provider.
    """

    def __init__(
        self,
        provider: str = "stub",
        smtp_host: str = None,
        smtp_port: int = 587,
        smtp_user: str = None,
        smtp_password: str = None,
        from_email: str = "noreply@datagod.com",
        from_name: str = "DataGod"
    ):
        """
        Initialize the email service.

        Args:
            provider: Email provider ('stub', 'smtp', 'sendgrid', 'ses')
            smtp_host: SMTP server host (if using SMTP)
            smtp_port: SMTP server port (if using SMTP)
            smtp_user: SMTP username (if using SMTP)
            smtp_password: SMTP password (if using SMTP)
            from_email: Default sender email address
            from_name: Default sender name
        """
        self.provider = provider
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.from_name = from_name

        logger.info(f"EmailService initialized with provider: {provider}")

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None
    ) -> bool:
        """
        Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body_text: Plain text body
            body_html: Optional HTML body
            from_email: Override default from email
            from_name: Override default from name

        Returns:
            bool: True if email was sent (or logged) successfully
        """
        sender_email = from_email or self.from_email
        sender_name = from_name or self.from_name

        if self.provider == "stub":
            return self._send_stub(to_email, subject, body_text, body_html, sender_email, sender_name)
        elif self.provider == "smtp":
            return self._send_smtp(to_email, subject, body_text, body_html, sender_email, sender_name)
        else:
            logger.error(f"Unknown email provider: {self.provider}")
            return False

    def _send_stub(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str],
        from_email: str,
        from_name: str
    ) -> bool:
        """Stub implementation - logs email content instead of sending."""
        logger.info("=" * 60)
        logger.info("EMAIL STUB - Would send email:")
        logger.info(f"  From: {from_name} <{from_email}>")
        logger.info(f"  To: {to_email}")
        logger.info(f"  Subject: {subject}")
        logger.info(f"  Body (text):\n{body_text}")
        if body_html:
            logger.info(f"  Body (HTML): [HTML content available]")
        logger.info("=" * 60)
        return True

    def _send_smtp(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str],
        from_email: str,
        from_name: str
    ) -> bool:
        """Send email via SMTP."""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{from_name} <{from_email}>"
            msg['To'] = to_email

            # Attach text part
            part1 = MIMEText(body_text, 'plain')
            msg.attach(part1)

            # Attach HTML part if provided
            if body_html:
                part2 = MIMEText(body_html, 'html')
                msg.attach(part2)

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.sendmail(from_email, to_email, msg.as_string())

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def send_password_reset(
        self,
        to_email: str,
        username: str,
        reset_token: str,
        reset_url: str = None,
        expires_hours: int = 1
    ) -> bool:
        """
        Send password reset email.

        Args:
            to_email: User's email address
            username: User's username
            reset_token: Password reset token
            reset_url: Optional full reset URL (if not provided, token is included)
            expires_hours: Hours until token expires

        Returns:
            bool: True if email was sent successfully
        """
        if reset_url is None:
            reset_url = f"https://datagod.com/reset-password?token={reset_token}"

        subject = "DataGod - Password Reset Request"

        body_text = f"""
Hello {username},

You have requested to reset your password for your DataGod account.

Click the link below to reset your password:
{reset_url}

This link will expire in {expires_hours} hour(s).

If you did not request a password reset, please ignore this email.
Your password will remain unchanged.

For security reasons, do not share this link with anyone.

Best regards,
The DataGod Team
"""

        body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .button {{
            display: inline-block;
            padding: 12px 24px;
            background-color: #007bff;
            color: white !important;
            text-decoration: none;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .warning {{ color: #856404; background-color: #fff3cd; padding: 10px; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Password Reset Request</h2>
        <p>Hello {username},</p>
        <p>You have requested to reset your password for your DataGod account.</p>
        <p>Click the button below to reset your password:</p>
        <a href="{reset_url}" class="button">Reset Password</a>
        <p>This link will expire in <strong>{expires_hours} hour(s)</strong>.</p>
        <div class="warning">
            <strong>Security Notice:</strong> If you did not request a password reset,
            please ignore this email. Your password will remain unchanged.
        </div>
        <p>For security reasons, do not share this link with anyone.</p>
        <p>Best regards,<br>The DataGod Team</p>
    </div>
</body>
</html>
"""

        return self.send_email(to_email, subject, body_text, body_html)

    def send_welcome_email(
        self,
        to_email: str,
        username: str
    ) -> bool:
        """
        Send welcome email to new users.

        Args:
            to_email: User's email address
            username: User's username

        Returns:
            bool: True if email was sent successfully
        """
        subject = "Welcome to DataGod!"

        body_text = f"""
Hello {username},

Welcome to DataGod - your comprehensive public records data platform!

Your account has been created successfully. You can now:

- Search millions of property records across the United States
- Export data in various formats (CSV, JSON, Excel)
- Set up alerts for new records matching your criteria
- Access our powerful API for integration

To get started, log in at: https://datagod.com/login

If you have any questions, please don't hesitate to reach out to our support team.

Best regards,
The DataGod Team
"""

        body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .button {{
            display: inline-block;
            padding: 12px 24px;
            background-color: #28a745;
            color: white !important;
            text-decoration: none;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .feature {{ padding: 10px 0; border-bottom: 1px solid #eee; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Welcome to DataGod!</h2>
        <p>Hello {username},</p>
        <p>Welcome to DataGod - your comprehensive public records data platform!</p>
        <p>Your account has been created successfully. You can now:</p>
        <div class="feature">🔍 Search millions of property records across the United States</div>
        <div class="feature">📊 Export data in various formats (CSV, JSON, Excel)</div>
        <div class="feature">🔔 Set up alerts for new records matching your criteria</div>
        <div class="feature">🔌 Access our powerful API for integration</div>
        <a href="https://datagod.com/login" class="button">Get Started</a>
        <p>If you have any questions, please don't hesitate to reach out to our support team.</p>
        <p>Best regards,<br>The DataGod Team</p>
    </div>
</body>
</html>
"""

        return self.send_email(to_email, subject, body_text, body_html)

    def send_email_verification(
        self,
        to_email: str,
        username: str,
        verification_token: str,
        verification_url: str = None
    ) -> bool:
        """
        Send email verification link.

        Args:
            to_email: User's email address
            username: User's username
            verification_token: Email verification token
            verification_url: Optional full verification URL

        Returns:
            bool: True if email was sent successfully
        """
        if verification_url is None:
            verification_url = f"https://datagod.com/verify-email?token={verification_token}"

        subject = "DataGod - Verify Your Email Address"

        body_text = f"""
Hello {username},

Thank you for registering with DataGod!

Please verify your email address by clicking the link below:
{verification_url}

If you did not create an account with DataGod, please ignore this email.

Best regards,
The DataGod Team
"""

        return self.send_email(to_email, subject, body_text)


# Global instance (can be configured at startup)
email_service = EmailService()


def get_email_service() -> EmailService:
    """Get the global email service instance."""
    return email_service


def configure_email_service(**kwargs):
    """Configure the global email service with new settings."""
    global email_service
    email_service = EmailService(**kwargs)
    return email_service
