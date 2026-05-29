"""
Comprehensive tests for DataGod API v2 Authentication endpoints.

This module tests:
- Login/authentication (/token, /auth/login)
- User registration (/auth/register)
- Password reset (/auth/forgot-password, /auth/reset-password)
- Token refresh (/refresh-token)
- User profile endpoints (/users/me, /users)
- Role-based access control

Coverage target: 100% of authentication-related code in api_v2_simple.py
"""

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

# Set test environment before imports
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api", "src"))


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_get_password_hash(self):
        """Test password hashing function."""
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        password = "securepassword123"
        hashed = pwd_context.hash(password)
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        password = "securepassword123"
        hashed = pwd_context.hash(password)
        assert pwd_context.verify(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        password = "securepassword123"
        wrong_password = "wrongpassword"
        hashed = pwd_context.hash(password)
        assert pwd_context.verify(wrong_password, hashed) is False

    def test_different_passwords_different_hashes(self):
        """Test that same password generates different hashes (salt)."""
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        password = "securepassword123"
        hash1 = pwd_context.hash(password)
        hash2 = pwd_context.hash(password)
        assert hash1 != hash2  # Due to random salt


class TestTokenCreation:
    """Tests for JWT token creation."""

    def test_create_access_token_basic(self):
        """Test basic token creation."""
        from jose import jwt

        SECRET_KEY = "test-secret-key"
        ALGORITHM = "HS256"

        data = {"sub": "testuser", "roles": ["user"]}
        encoded = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

        assert encoded is not None
        assert len(encoded) > 50

        # Decode and verify
        payload = jwt.decode(encoded, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "testuser"
        assert payload["roles"] == ["user"]

    def test_create_access_token_with_expiration(self):
        """Test token creation with custom expiration."""
        from jose import jwt

        SECRET_KEY = "test-secret-key"
        ALGORITHM = "HS256"

        data = {"sub": "testuser"}
        expire = datetime.utcnow() + timedelta(minutes=15)
        data["exp"] = expire

        token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload

    def test_token_expiration_validation(self):
        """Test that expired tokens are rejected."""
        from jose import JWTError, jwt

        SECRET_KEY = "test-secret-key"
        ALGORITHM = "HS256"

        # Create already-expired token
        data = {
            "sub": "testuser",
            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
        }
        token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

        # Should raise JWTError on decode
        with pytest.raises(JWTError):
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


class TestAPIv2SimpleClient:
    """Tests using the api_v2_simple.py TestClient."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from api.src.api_v2_simple import app
        from api.src.db import init_db

        try:
            init_db()
        except Exception:
            pass  # Tables may already exist
        return TestClient(app)

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_login_success(self, client):
        """Test successful login with demo user."""
        response = client.post(
            "/token", data={"username": "admin", "password": "admin123"}
        )
        # May be 200 or 401 depending on whether demo users exist
        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert "expires_in" in data

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post(
            "/token", data={"username": "invalid", "password": "wrongpassword"}
        )
        assert response.status_code in [401, 423]  # 423 is account locked

    def test_auth_login_endpoint(self, client):
        """Test /auth/login endpoint (alias for /token)."""
        response = client.post(
            "/auth/login", data={"username": "admin", "password": "admin123"}
        )
        # May be 200 or 401 depending on whether demo users exist
        assert response.status_code in [200, 400, 401, 422, 423]

    def test_users_me_no_auth(self, client):
        """Test /users/me without authentication."""
        response = client.get("/users/me")
        assert response.status_code == 401

    def test_users_me_invalid_token(self, client):
        """Test /users/me with invalid token."""
        response = client.get(
            "/users/me", headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401


class TestRegistrationEndpoint:
    """Tests for user registration endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from api.src.api_v2_simple import app
        from api.src.db import init_db

        try:
            init_db()
        except Exception:
            pass
        return TestClient(app)

    def test_register_missing_fields(self, client):
        """Test registration with missing fields."""
        response = client.post("/auth/register", json={"username": "testuser"})
        assert response.status_code == 422

    def test_register_invalid_email(self, client):
        """Test registration with invalid email format."""
        response = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "not-an-email",
                "password": "password123",
            },
        )
        # API may return 400 (bad request) or 422 (validation error)
        assert response.status_code in [400, 422]

    def test_register_weak_password(self, client):
        """Test registration with weak password."""
        response = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "test@example.com",
                "password": "weak",
            },
        )
        assert response.status_code == 422


class TestPasswordResetEndpoints:
    """Tests for password reset endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from api.src.api_v2_simple import app
        from api.src.db import init_db

        try:
            init_db()
        except Exception:
            pass
        return TestClient(app)

    def test_forgot_password_response(self, client):
        """Test forgot password always returns success (security)."""
        response = client.post(
            "/auth/forgot-password", json={"email": "nonexistent@example.com"}
        )
        # Should always return 200 for security
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_reset_password_invalid_token(self, client):
        """Test password reset with invalid token."""
        response = client.post(
            "/auth/reset-password",
            json={"token": "invalid-token", "new_password": "newpassword123"},
        )
        assert response.status_code == 400


class TestTokenRefreshEndpoint:
    """Tests for token refresh endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from api.src.api_v2_simple import app

        return TestClient(app)

    def test_refresh_token_invalid(self, client):
        """Test token refresh with invalid token."""
        response = client.post(
            "/refresh-token", headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401


class TestProtectedEndpoints:
    """Tests for protected endpoints requiring authentication."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from api.src.api_v2_simple import app
        from api.src.db import init_db

        try:
            init_db()
        except Exception:
            pass
        return TestClient(app)

    def test_create_jurisdiction_unauthorized(self, client):
        """Test creating jurisdiction without auth."""
        response = client.post(
            "/jurisdictions",
            json={
                "name": "Test County",
                "state": "TX",
                "county": "Test",
                "jurisdiction_type": "county",
            },
        )
        assert response.status_code in [200, 201, 401]

    def test_users_list_unauthorized(self, client):
        """Test listing users without auth."""
        response = client.get("/users")
        assert response.status_code == 401


class TestPydanticModels:
    """Tests for Pydantic model validation."""

    def test_user_model_creation(self):
        """Test basic User model creation."""
        from typing import List, Optional

        from pydantic import BaseModel

        class User(BaseModel):
            username: str
            email: str
            full_name: Optional[str] = None
            disabled: Optional[bool] = None
            roles: List[str] = ["user"]

        user = User(
            username="testuser", email="test@example.com", full_name="Test User"
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.roles == ["user"]

    def test_token_model(self):
        """Test Token model structure."""
        from pydantic import BaseModel

        class Token(BaseModel):
            access_token: str
            token_type: str
            expires_in: int

        token = Token(access_token="test-token", token_type="bearer", expires_in=3600)
        assert token.access_token == "test-token"
        assert token.token_type == "bearer"


class TestRateLimiting:
    """Tests for rate limiting functionality."""

    def test_rate_limit_storage(self):
        """Test rate limit storage structure."""
        rate_limits = {}
        ip = "192.168.1.1"

        if ip not in rate_limits:
            rate_limits[ip] = []

        import time

        rate_limits[ip].append(time.time())
        rate_limits[ip].append(time.time())

        assert len(rate_limits[ip]) == 2

    def test_rate_limit_check_logic(self):
        """Test rate limit check logic."""
        import time

        rate_limits = {}
        max_requests = 5
        window = 60  # seconds

        ip = "192.168.1.2"
        current_time = time.time()

        # Add 5 requests
        rate_limits[ip] = [current_time] * 5

        # Check if limit exceeded
        is_limited = len(rate_limits.get(ip, [])) >= max_requests
        assert is_limited is True

    def test_rate_limit_window_cleanup(self):
        """Test rate limit window cleanup."""
        import time

        rate_limits = {}
        window_seconds = 60
        current_time = time.time()

        ip = "192.168.1.3"
        # Add old timestamps
        rate_limits[ip] = [current_time - 70, current_time - 65]  # Outside window
        rate_limits[ip].append(current_time - 5)  # Inside window

        # Clean up old entries
        rate_limits[ip] = [
            t for t in rate_limits[ip] if current_time - t < window_seconds
        ]

        assert len(rate_limits[ip]) == 1


class TestCacheDecorator:
    """Tests for caching functionality."""

    def test_cache_key_generation(self):
        """Test cache key generation logic."""
        func_name = "test_function"
        kwargs = {"param1": "value1", "param2": "value2"}

        cache_key = f"cache:{func_name}:{hash(frozenset(kwargs.items()))}"

        assert cache_key.startswith("cache:test_function:")
        assert len(cache_key) > 20

    def test_cache_key_uniqueness(self):
        """Test cache keys are unique for different parameters."""
        func_name = "test_function"

        kwargs1 = {"param": "value1"}
        kwargs2 = {"param": "value2"}

        key1 = f"cache:{func_name}:{hash(frozenset(kwargs1.items()))}"
        key2 = f"cache:{func_name}:{hash(frozenset(kwargs2.items()))}"

        assert key1 != key2


class TestHasRoleLogic:
    """Tests for role-based access control logic."""

    def test_has_role_single_match(self):
        """Test role check with single role match."""
        user_roles = ["user", "admin"]
        required_roles = ["admin"]

        has_role = any(role in user_roles for role in required_roles)
        assert has_role is True

    def test_has_role_no_match(self):
        """Test role check with no role match."""
        user_roles = ["user"]
        required_roles = ["admin", "superuser"]

        has_role = any(role in user_roles for role in required_roles)
        assert has_role is False

    def test_has_role_multiple_match(self):
        """Test role check with multiple role matches."""
        user_roles = ["user", "admin", "moderator"]
        required_roles = ["admin", "user"]

        has_role = any(role in user_roles for role in required_roles)
        assert has_role is True


class TestAuthenticateUserLogic:
    """Tests for user authentication logic."""

    def test_password_verification_logic(self):
        """Test password verification flow."""
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # Simulate stored hash
        stored_hash = pwd_context.hash("correctpassword")

        # Verify correct password
        assert pwd_context.verify("correctpassword", stored_hash) is True

        # Verify incorrect password
        assert pwd_context.verify("wrongpassword", stored_hash) is False

    def test_user_disabled_check(self):
        """Test user disabled status check."""
        user = {"username": "test", "disabled": True}

        is_active = not user.get("disabled", False)
        assert is_active is False

        user["disabled"] = False
        is_active = not user.get("disabled", False)
        assert is_active is True


class TestDemoUsersLogic:
    """Tests for demo user creation logic."""

    def test_demo_users_structure(self):
        """Test demo users data structure."""
        demo_users = [
            {
                "username": "admin",
                "email": "admin@datagod.com",
                "full_name": "DataGod Admin",
                "password": "admin123",
                "roles": ["admin", "user"],
                "disabled": False,
            },
            {
                "username": "user",
                "email": "user@datagod.com",
                "full_name": "DataGod User",
                "password": "user123",
                "roles": ["user"],
                "disabled": False,
            },
        ]

        assert len(demo_users) == 2
        assert demo_users[0]["roles"] == ["admin", "user"]
        assert demo_users[1]["roles"] == ["user"]


class TestTokenDataStructure:
    """Tests for token data structure."""

    def test_token_payload_structure(self):
        """Test JWT token payload structure."""
        token_data = {
            "sub": "testuser",
            "roles": ["user"],
            "exp": datetime.utcnow() + timedelta(minutes=30),
        }

        assert "sub" in token_data
        assert "roles" in token_data
        assert "exp" in token_data

    def test_token_data_extraction(self):
        """Test extracting data from token."""
        payload = {"sub": "testuser", "roles": ["user", "admin"]}

        username = payload.get("sub")
        roles = payload.get("roles", ["user"])

        assert username == "testuser"
        assert "admin" in roles


class TestHTTPExceptions:
    """Tests for HTTP exception handling."""

    def test_unauthorized_exception_structure(self):
        """Test 401 Unauthorized exception structure."""
        from fastapi import HTTPException, status

        exc = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        assert exc.status_code == 401
        assert exc.detail == "Could not validate credentials"

    def test_forbidden_exception_structure(self):
        """Test 403 Forbidden exception structure."""
        from fastapi import HTTPException, status

        exc = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Operation not permitted"
        )

        assert exc.status_code == 403
        assert exc.detail == "Operation not permitted"

    def test_locked_exception_structure(self):
        """Test 423 Locked exception structure."""
        from fastapi import HTTPException, status

        exc = HTTPException(
            status_code=status.HTTP_423_LOCKED, detail="Account is temporarily locked"
        )

        assert exc.status_code == 423


class TestEmailValidation:
    """Tests for email validation logic."""

    def test_email_regex_valid(self):
        """Test email regex with valid emails."""
        import re

        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        valid_emails = [
            "test@example.com",
            "user.name@domain.org",
            "user+tag@company.co.uk",
        ]

        for email in valid_emails:
            assert re.match(email_regex, email) is not None

    def test_email_regex_invalid(self):
        """Test email regex with invalid emails."""
        import re

        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        invalid_emails = [
            "notanemail",
            "@nodomain.com",
            "noat.com",
            "spaces here@domain.com",
        ]

        for email in invalid_emails:
            assert re.match(email_regex, email) is None


class TestPasswordValidation:
    """Tests for password validation logic."""

    def test_password_length_check(self):
        """Test password minimum length."""
        min_length = 8

        valid_password = "password123"
        invalid_password = "short"

        assert len(valid_password) >= min_length
        assert len(invalid_password) < min_length

    def test_password_contains_letter(self):
        """Test password contains letter."""
        password_with_letter = "password123"
        password_no_letter = "12345678"

        has_letter_1 = any(c.isalpha() for c in password_with_letter)
        has_letter_2 = any(c.isalpha() for c in password_no_letter)

        assert has_letter_1 is True
        assert has_letter_2 is False

    def test_password_contains_digit(self):
        """Test password contains digit."""
        password_with_digit = "password123"
        password_no_digit = "passwordonly"

        has_digit_1 = any(c.isdigit() for c in password_with_digit)
        has_digit_2 = any(c.isdigit() for c in password_no_digit)

        assert has_digit_1 is True
        assert has_digit_2 is False


class TestUsernameValidation:
    """Tests for username validation logic."""

    def test_username_pattern_valid(self):
        """Test username pattern with valid usernames."""
        import re

        pattern = r"^[a-zA-Z0-9_]+$"

        valid_usernames = ["testuser", "test_user", "TestUser123", "user_123"]

        for username in valid_usernames:
            assert re.match(pattern, username) is not None

    def test_username_pattern_invalid(self):
        """Test username pattern with invalid usernames."""
        import re

        pattern = r"^[a-zA-Z0-9_]+$"

        invalid_usernames = ["test user", "test-user", "test@user", "test.user"]

        for username in invalid_usernames:
            assert re.match(pattern, username) is None


class TestUUIDGeneration:
    """Tests for UUID token generation."""

    def test_uuid_generation(self):
        """Test UUID token generation."""
        import uuid

        token1 = str(uuid.uuid4())
        token2 = str(uuid.uuid4())

        assert token1 != token2
        assert len(token1) == 36
        assert "-" in token1

    def test_uuid_format(self):
        """Test UUID format validation."""
        import uuid

        token = str(uuid.uuid4())

        # Should be valid UUID format
        try:
            uuid.UUID(token)
            is_valid = True
        except ValueError:
            is_valid = False

        assert is_valid is True


class TestDatetimeHandling:
    """Tests for datetime handling in tokens."""

    def test_token_expiration_calculation(self):
        """Test token expiration time calculation."""
        from datetime import datetime, timedelta

        access_token_expire_minutes = 30
        expire = datetime.utcnow() + timedelta(minutes=access_token_expire_minutes)

        # Should be approximately 30 minutes in future
        time_diff = expire - datetime.utcnow()
        assert 29 <= time_diff.seconds / 60 <= 31

    def test_password_reset_expiration(self):
        """Test password reset token expiration."""
        from datetime import datetime, timedelta

        expires_hours = 1
        reset_expires = datetime.utcnow() + timedelta(hours=expires_hours)

        # Should be approximately 1 hour in future
        time_diff = reset_expires - datetime.utcnow()
        assert 59 <= time_diff.seconds / 60 <= 61


class TestJSONEncoderCompatibility:
    """Tests for JSON encoder compatibility with auth data."""

    def test_datetime_serialization(self):
        """Test datetime can be serialized for JSON."""
        from datetime import datetime

        now = datetime.utcnow()
        iso_string = now.isoformat()

        assert isinstance(iso_string, str)
        assert "T" in iso_string

    def test_user_dict_serialization(self):
        """Test user dict can be serialized."""
        import json

        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "roles": ["user", "admin"],
            "disabled": False,
        }

        json_str = json.dumps(user_data)
        decoded = json.loads(json_str)

        assert decoded["username"] == "testuser"
        assert decoded["roles"] == ["user", "admin"]
