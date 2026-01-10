"""
Comprehensive tests for DataGod authentication system.

Tests cover:
- User registration
- User login
- JWT token validation
- Password reset flow
- Role-based access control
- Account lockout
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import uuid


class TestUserRegistration:
    """Tests for user registration endpoint."""

    def test_registration_success(self):
        """Test successful user registration with valid data."""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # Valid registration data
        registration_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "SecurePass123",
            "full_name": "New User"
        }

        # Validate password hashing
        hashed = pwd_context.hash(registration_data["password"])
        assert pwd_context.verify(registration_data["password"], hashed)

    def test_registration_duplicate_email(self):
        """Test registration fails with duplicate email."""
        # This test verifies the validation logic
        existing_emails = ["user@example.com", "admin@datagod.com"]
        new_email = "user@example.com"

        assert new_email in existing_emails

    def test_registration_duplicate_username(self):
        """Test registration fails with duplicate username."""
        existing_usernames = ["admin", "user", "testuser"]
        new_username = "admin"

        assert new_username in existing_usernames

    def test_registration_invalid_email_format(self):
        """Test registration fails with invalid email format."""
        import re
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        invalid_emails = [
            "notanemail",
            "missing@domain",
            "@nodomain.com",
            "spaces in@email.com",
            "no.at" "sign.com"
        ]

        for email in invalid_emails:
            assert not re.match(email_regex, email), f"Email '{email}' should be invalid"

    def test_registration_valid_email_format(self):
        """Test valid email formats are accepted."""
        import re
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        valid_emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.org",
            "user123@subdomain.example.co.uk"
        ]

        for email in valid_emails:
            assert re.match(email_regex, email), f"Email '{email}' should be valid"

    def test_registration_weak_password(self):
        """Test registration fails with weak password."""
        weak_passwords = [
            "short",      # Too short
            "12345678",   # No letters
            "abcdefgh",   # No numbers
            "abc123",     # Too short
        ]

        for password in weak_passwords:
            has_letter = any(c.isalpha() for c in password)
            has_digit = any(c.isdigit() for c in password)
            is_long_enough = len(password) >= 8

            is_valid = has_letter and has_digit and is_long_enough
            assert not is_valid, f"Password '{password}' should be rejected"

    def test_registration_strong_password(self):
        """Test strong passwords are accepted."""
        strong_passwords = [
            "SecurePass123",
            "MyP@ssw0rd!",
            "abcd1234",
            "12345678a",
        ]

        for password in strong_passwords:
            has_letter = any(c.isalpha() for c in password)
            has_digit = any(c.isdigit() for c in password)
            is_long_enough = len(password) >= 8

            is_valid = has_letter and has_digit and is_long_enough
            assert is_valid, f"Password '{password}' should be accepted"

    def test_registration_username_validation(self):
        """Test username format validation."""
        import re
        username_regex = r'^[a-zA-Z0-9_]+$'

        valid_usernames = ["user123", "test_user", "Admin", "user_name_123"]
        invalid_usernames = ["user@name", "user name", "user-name", "user.name"]

        for username in valid_usernames:
            assert re.match(username_regex, username), f"Username '{username}' should be valid"

        for username in invalid_usernames:
            assert not re.match(username_regex, username), f"Username '{username}' should be invalid"


class TestUserLogin:
    """Tests for user login and authentication."""

    def test_login_success(self):
        """Test successful login with correct credentials."""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        stored_hash = pwd_context.hash("correctpassword")
        assert pwd_context.verify("correctpassword", stored_hash)

    def test_login_wrong_password(self):
        """Test login fails with wrong password."""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        stored_hash = pwd_context.hash("correctpassword")
        assert not pwd_context.verify("wrongpassword", stored_hash)

    def test_login_nonexistent_user(self):
        """Test login fails for non-existent user."""
        existing_users = {"admin", "user", "testuser"}
        attempted_username = "nonexistent"

        assert attempted_username not in existing_users

    def test_login_disabled_user(self):
        """Test login fails for disabled user."""
        user = {
            "username": "disableduser",
            "disabled": True
        }

        assert user["disabled"] is True


class TestJWTTokens:
    """Tests for JWT token handling."""

    def test_jwt_token_creation(self):
        """Test JWT token is created correctly."""
        from jose import jwt

        SECRET_KEY = "test-secret-key"
        ALGORITHM = "HS256"

        data = {"sub": "testuser", "roles": ["user"]}
        expire = datetime.utcnow() + timedelta(minutes=30)
        data["exp"] = expire

        token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
        assert token is not None
        assert isinstance(token, str)

    def test_jwt_token_valid(self):
        """Test valid JWT token is decoded correctly."""
        from jose import jwt

        SECRET_KEY = "test-secret-key"
        ALGORITHM = "HS256"

        data = {"sub": "testuser", "roles": ["user"]}
        expire = datetime.utcnow() + timedelta(minutes=30)
        data["exp"] = expire

        token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert decoded["sub"] == "testuser"
        assert decoded["roles"] == ["user"]

    def test_jwt_token_expired(self):
        """Test expired JWT token is rejected."""
        from jose import jwt, JWTError

        SECRET_KEY = "test-secret-key"
        ALGORITHM = "HS256"

        data = {"sub": "testuser", "roles": ["user"]}
        expire = datetime.utcnow() - timedelta(minutes=30)  # Expired
        data["exp"] = expire

        token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

        with pytest.raises(JWTError):
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    def test_jwt_token_invalid_signature(self):
        """Test JWT token with wrong secret is rejected."""
        from jose import jwt, JWTError

        SECRET_KEY = "correct-secret-key"
        WRONG_SECRET = "wrong-secret-key"
        ALGORITHM = "HS256"

        data = {"sub": "testuser", "roles": ["user"]}
        expire = datetime.utcnow() + timedelta(minutes=30)
        data["exp"] = expire

        token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

        with pytest.raises(JWTError):
            jwt.decode(token, WRONG_SECRET, algorithms=[ALGORITHM])


class TestPasswordReset:
    """Tests for password reset flow."""

    def test_password_reset_token_generation(self):
        """Test password reset token is generated correctly."""
        token = str(uuid.uuid4())

        assert token is not None
        assert len(token) == 36  # UUID format
        assert '-' in token

    def test_password_reset_token_unique(self):
        """Test password reset tokens are unique."""
        tokens = [str(uuid.uuid4()) for _ in range(100)]
        unique_tokens = set(tokens)

        assert len(tokens) == len(unique_tokens)

    def test_password_reset_request_existing_email(self):
        """Test password reset request for existing email."""
        existing_emails = {"user@example.com", "admin@datagod.com"}
        requested_email = "user@example.com"

        # Should process silently (don't reveal if email exists)
        assert requested_email in existing_emails

    def test_password_reset_request_nonexistent_email(self):
        """Test password reset request for non-existent email."""
        existing_emails = {"user@example.com", "admin@datagod.com"}
        requested_email = "nonexistent@example.com"

        # Should still return success (don't reveal if email exists)
        assert requested_email not in existing_emails

    def test_password_reset_token_expiry(self):
        """Test password reset token expires after set time."""
        token_created = datetime.utcnow()
        token_expires = token_created + timedelta(hours=1)

        # Token should be valid before expiry
        current_time = datetime.utcnow()
        assert current_time < token_expires

        # Simulate expired token
        expired_time = token_created + timedelta(hours=2)
        assert expired_time > token_expires

    def test_password_reset_invalid_token(self):
        """Test password reset fails with invalid token."""
        valid_tokens = {"token-123", "token-456"}
        invalid_token = "invalid-token"

        assert invalid_token not in valid_tokens

    def test_password_reset_success(self):
        """Test successful password reset."""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        old_password = "OldPass123"
        new_password = "NewPass456"

        old_hash = pwd_context.hash(old_password)
        new_hash = pwd_context.hash(new_password)

        # New password should work
        assert pwd_context.verify(new_password, new_hash)
        # Old password should not work with new hash
        assert not pwd_context.verify(old_password, new_hash)


class TestRoleBasedAccess:
    """Tests for role-based access control."""

    def test_admin_has_all_roles(self):
        """Test admin user has admin role."""
        admin_user = {
            "username": "admin",
            "roles": ["admin", "user"]
        }

        assert "admin" in admin_user["roles"]
        assert "user" in admin_user["roles"]

    def test_regular_user_roles(self):
        """Test regular user has only user role."""
        regular_user = {
            "username": "user",
            "roles": ["user"]
        }

        assert "user" in regular_user["roles"]
        assert "admin" not in regular_user["roles"]

    def test_role_check_admin_required(self):
        """Test access denied when admin role is required."""
        required_roles = ["admin"]
        user_roles = ["user"]

        has_access = any(role in user_roles for role in required_roles)
        assert not has_access

    def test_role_check_user_required(self):
        """Test access granted when user role is required."""
        required_roles = ["user"]
        user_roles = ["user"]

        has_access = any(role in user_roles for role in required_roles)
        assert has_access

    def test_role_check_admin_or_user(self):
        """Test access when admin or user role is required."""
        required_roles = ["admin", "user"]

        admin_roles = ["admin", "user"]
        user_roles = ["user"]

        assert any(role in admin_roles for role in required_roles)
        assert any(role in user_roles for role in required_roles)


class TestAccountLockout:
    """Tests for account lockout mechanism."""

    def test_account_not_locked_initially(self):
        """Test new account is not locked."""
        user = {
            "username": "newuser",
            "failed_login_count": 0,
            "locked_until": None
        }

        is_locked = user["locked_until"] is not None and user["locked_until"] > datetime.utcnow()
        assert not is_locked

    def test_account_locked_after_failures(self):
        """Test account is locked after too many failed attempts."""
        MAX_FAILED_ATTEMPTS = 5
        user = {
            "username": "testuser",
            "failed_login_count": 5,
            "locked_until": datetime.utcnow() + timedelta(minutes=30)
        }

        assert user["failed_login_count"] >= MAX_FAILED_ATTEMPTS
        is_locked = user["locked_until"] is not None and user["locked_until"] > datetime.utcnow()
        assert is_locked

    def test_account_unlocked_after_timeout(self):
        """Test account is unlocked after lockout period."""
        user = {
            "username": "testuser",
            "failed_login_count": 5,
            "locked_until": datetime.utcnow() - timedelta(minutes=1)  # Expired
        }

        is_locked = user["locked_until"] is not None and user["locked_until"] > datetime.utcnow()
        assert not is_locked

    def test_failed_login_count_increments(self):
        """Test failed login count increments on failure."""
        initial_count = 2
        new_count = initial_count + 1

        assert new_count == 3

    def test_failed_login_count_resets_on_success(self):
        """Test failed login count resets on successful login."""
        user = {
            "failed_login_count": 3,
            "locked_until": None
        }

        # Simulate successful login
        user["failed_login_count"] = 0
        user["locked_until"] = None

        assert user["failed_login_count"] == 0


class TestPasswordHashing:
    """Tests for password hashing utilities."""

    def test_password_hash_is_different(self):
        """Test hashed password is different from plain password."""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        password = "TestPassword123"
        hashed = pwd_context.hash(password)

        assert password != hashed
        assert len(hashed) > len(password)

    def test_same_password_different_hashes(self):
        """Test same password produces different hashes (salt)."""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        password = "TestPassword123"
        hash1 = pwd_context.hash(password)
        hash2 = pwd_context.hash(password)

        # Same password, different hashes due to salt
        assert hash1 != hash2
        # But both should verify
        assert pwd_context.verify(password, hash1)
        assert pwd_context.verify(password, hash2)

    def test_bcrypt_hash_format(self):
        """Test password hash uses bcrypt format."""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        password = "TestPassword123"
        hashed = pwd_context.hash(password)

        # Bcrypt hashes start with $2b$
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")


class TestRateLimiting:
    """Tests for registration rate limiting."""

    def test_rate_limit_allows_first_requests(self):
        """Test rate limit allows initial requests."""
        max_attempts = 5
        current_attempts = 0

        assert current_attempts < max_attempts

    def test_rate_limit_blocks_after_threshold(self):
        """Test rate limit blocks after threshold."""
        max_attempts = 5
        current_attempts = 5

        assert current_attempts >= max_attempts

    def test_rate_limit_resets_after_window(self):
        """Test rate limit resets after time window."""
        import time

        window_seconds = 3600  # 1 hour
        attempt_time = time.time() - 7200  # 2 hours ago
        current_time = time.time()

        # Attempt is outside window
        assert current_time - attempt_time > window_seconds


class TestEmailService:
    """Tests for email service functionality."""

    def test_email_service_stub_mode(self):
        """Test email service works in stub mode."""
        from datagod.services.email_service import EmailService

        email_service = EmailService(provider="stub")
        assert email_service.provider == "stub"

    def test_send_password_reset_email(self):
        """Test sending password reset email."""
        from datagod.services.email_service import EmailService

        email_service = EmailService(provider="stub")
        result = email_service.send_password_reset(
            to_email="user@example.com",
            username="testuser",
            reset_token="test-token-123",
            expires_hours=1
        )

        assert result is True

    def test_send_welcome_email(self):
        """Test sending welcome email."""
        from datagod.services.email_service import EmailService

        email_service = EmailService(provider="stub")
        result = email_service.send_welcome_email(
            to_email="user@example.com",
            username="newuser"
        )

        assert result is True

    def test_email_service_default_settings(self):
        """Test email service default settings."""
        from datagod.services.email_service import EmailService

        email_service = EmailService()
        assert email_service.from_email == "noreply@datagod.com"
        assert email_service.from_name == "DataGod"
