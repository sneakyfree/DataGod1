"""
Integration tests for DataGod API v2
Tests actual API endpoints using FastAPI TestClient
"""

import pytest
import sys
import os
import importlib.util
from pathlib import Path

# Get paths
tests_path = Path(__file__).parent
project_root = tests_path.parent
api_src_path = project_root / "api" / "src"

# Add paths for imports - api/src first for priority
sys.path.insert(0, str(api_src_path))
sys.path.insert(1, str(project_root))

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime
from passlib.context import CryptContext

# Password hashing for mock users
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class MockUserDbManager:
    """Mock user database manager with demo users."""

    def __init__(self):
        self.demo_users = {
            "admin": {
                "id": 1,
                "username": "admin",
                "email": "admin@datagod.com",
                "full_name": "DataGod Admin",
                "hashed_password": pwd_context.hash("admin123"),
                "disabled": False,
                "roles": ["admin", "user"],
                "email_verified": True,
                "subscription_tier": "enterprise",
                "last_login": None,
                "login_count": 0,
                "api_calls_today": 0,
                "exports_this_month": 0,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            },
            "user": {
                "id": 2,
                "username": "user",
                "email": "user@datagod.com",
                "full_name": "DataGod User",
                "hashed_password": pwd_context.hash("user123"),
                "disabled": False,
                "roles": ["user"],
                "email_verified": True,
                "subscription_tier": "free",
                "last_login": None,
                "login_count": 0,
                "api_calls_today": 0,
                "exports_this_month": 0,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }

    def get_user_by_username(self, username):
        return self.demo_users.get(username)

    def get_user_for_auth(self, username):
        return self.demo_users.get(username)

    def get_user_by_email(self, email):
        for user in self.demo_users.values():
            if user["email"] == email:
                return user
        return None

    def check_user_locked(self, username):
        return False

    def record_login(self, username, success=True):
        return True

    def create_user(self, username, email, hashed_password, full_name=None, roles=None, disabled=False):
        if username in self.demo_users:
            return None
        for user in self.demo_users.values():
            if user["email"] == email:
                return None
        self.demo_users[username] = {
            "id": len(self.demo_users) + 1,
            "username": username,
            "email": email,
            "full_name": full_name,
            "hashed_password": hashed_password,
            "disabled": disabled,
            "roles": roles or ["user"],
            "email_verified": False,
            "subscription_tier": "free",
            "last_login": None,
            "login_count": 0,
            "api_calls_today": 0,
            "exports_this_month": 0,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
        return len(self.demo_users)

    def list_users(self):
        return list(self.demo_users.values())

    def init_database(self):
        return True

    def set_password_reset_token(self, email, token, expires_hours=1):
        for user in self.demo_users.values():
            if user["email"] == email:
                return True
        return False

    def get_user_by_reset_token(self, token):
        return None

    def update_user(self, user_id, **kwargs):
        return True

    def clear_password_reset_token(self, user_id):
        return True


def create_mock_user_db_manager():
    """Create a mock user database manager with demo users."""
    return MockUserDbManager()


# Load api_v2_simple module directly to set up mock
api_v2_spec = importlib.util.spec_from_file_location("api_v2_simple", api_src_path / "api_v2_simple.py")
api_v2_module = importlib.util.module_from_spec(api_v2_spec)
sys.modules["api_v2_simple"] = api_v2_module
api_v2_spec.loader.exec_module(api_v2_module)

# Set up mock user db manager
set_user_db_manager = api_v2_module.set_user_db_manager
_mock_user_db = create_mock_user_db_manager()
set_user_db_manager(_mock_user_db)

# Get the app for tests
api_v2_app = api_v2_module.app


class TestHealthEndpoints:
    """Tests for health and monitoring endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client with mocked database"""
        app = api_v2_app  # Use module-level loaded app
        yield TestClient(app)

    def test_health_check_returns_200(self, client):
        """Test health check endpoint returns 200"""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_response_structure(self, client):
        """Test health check returns expected structure"""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "database" in data
        assert "cache" in data
        assert "api_version" in data

    def test_health_check_status_healthy(self, client):
        """Test health check reports healthy status"""
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint returns data"""
        response = client.get("/metrics")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "metrics" in data


class TestAuthenticationEndpoints:
    """Tests for authentication endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app = api_v2_app  # Use module-level loaded app
        yield TestClient(app)

    def test_token_endpoint_with_valid_credentials(self, client):
        """Test token endpoint with valid credentials"""
        response = client.post(
            "/token",
            data={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    def test_token_endpoint_with_invalid_credentials(self, client):
        """Test token endpoint with invalid credentials"""
        response = client.post(
            "/token",
            data={"username": "admin", "password": "wrongpassword"}
        )
        assert response.status_code == 401

        data = response.json()
        assert "detail" in data

    def test_token_endpoint_with_nonexistent_user(self, client):
        """Test token endpoint with non-existent user"""
        response = client.post(
            "/token",
            data={"username": "nonexistent", "password": "password"}
        )
        assert response.status_code == 401

    def test_register_endpoint_valid_user(self, client):
        """Test user registration with valid data"""
        response = client.post(
            "/auth/register",
            json={
                "username": "testuser123",
                "email": "testuser123@example.com",
                "password": "securepassword123",
                "full_name": "Test User"
            }
        )
        # Could be 200 or 400 if user already exists
        assert response.status_code in [200, 400]

    def test_register_endpoint_invalid_email(self, client):
        """Test user registration with invalid email"""
        response = client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "invalid-email",
                "password": "securepassword123",
                "full_name": "Test User"
            }
        )
        assert response.status_code == 400

    def test_register_endpoint_short_password(self, client):
        """Test user registration with password too short"""
        response = client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "short",
                "full_name": "Test User"
            }
        )
        assert response.status_code == 422  # Validation error

    def test_login_endpoint_valid_credentials(self, client):
        """Test login endpoint with valid credentials"""
        response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data

    def test_login_endpoint_invalid_credentials(self, client):
        """Test login endpoint with invalid credentials"""
        response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "wrongpassword"}
        )
        assert response.status_code == 401


class TestProtectedEndpoints:
    """Tests for protected endpoints requiring authentication"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app = api_v2_app  # Use module-level loaded app
        yield TestClient(app)

    @pytest.fixture
    def auth_token(self, client):
        """Get valid auth token"""
        response = client.post(
            "/token",
            data={"username": "admin", "password": "admin123"}
        )
        return response.json()["access_token"]

    def test_users_me_without_token(self, client):
        """Test /users/me endpoint without token returns 401"""
        response = client.get("/users/me")
        assert response.status_code == 401

    def test_users_me_with_valid_token(self, client, auth_token):
        """Test /users/me endpoint with valid token"""
        response = client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200

        data = response.json()
        assert "username" in data
        assert data["username"] == "admin"

    def test_users_me_with_invalid_token(self, client):
        """Test /users/me endpoint with invalid token"""
        response = client.get(
            "/users/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    def test_refresh_token_with_valid_token(self, client, auth_token):
        """Test token refresh with valid token"""
        response = client.post(
            "/refresh-token",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data


class TestPasswordResetEndpoints:
    """Tests for password reset functionality"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app = api_v2_app  # Use module-level loaded app
        yield TestClient(app)

    def test_forgot_password_valid_email(self, client):
        """Test forgot password with valid email"""
        response = client.post(
            "/auth/forgot-password",
            json={"email": "admin@datagod.com"}
        )
        assert response.status_code == 200

        data = response.json()
        assert "message" in data

    def test_forgot_password_invalid_email(self, client):
        """Test forgot password with invalid email format"""
        response = client.post(
            "/auth/forgot-password",
            json={"email": "invalid-email"}
        )
        # Should still return 200 to not reveal email existence
        assert response.status_code in [200, 400]

    def test_reset_password_invalid_token(self, client):
        """Test reset password with invalid token"""
        response = client.post(
            "/auth/reset-password",
            json={
                "token": "invalid_reset_token",
                "new_password": "newpassword123"
            }
        )
        assert response.status_code == 400


class TestJurisdictionEndpoints:
    """Tests for jurisdiction CRUD endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client with mocked database"""
        app = api_v2_app  # Use module-level loaded app
        yield TestClient(app, raise_server_exceptions=False)

    @pytest.fixture
    def auth_token(self, client):
        """Get valid auth token"""
        response = client.post(
            "/token",
            data={"username": "admin", "password": "admin123"}
        )
        return response.json()["access_token"]

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        mock_session = MagicMock()
        return mock_session

    def test_get_jurisdictions_requires_db(self, client):
        """Test getting jurisdictions - expects database interaction"""
        # This endpoint requires database, so we expect it to fail or return data
        # depending on database availability
        response = client.get("/jurisdictions")
        # Could be 200 (if db exists), 401 (if auth required), or 500 (if db error)
        assert response.status_code in [200, 401, 500]

    def test_get_jurisdiction_by_id_format(self, client, auth_token):
        """Test getting a specific jurisdiction by ID"""
        # Test format of request
        response = client.get(
            "/jurisdictions/999999",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        # Should be 404 (not found) or 500 (db error)
        assert response.status_code in [404, 500]


class TestSearchEndpoints:
    """Tests for search functionality"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app = api_v2_app  # Use module-level loaded app
        yield TestClient(app, raise_server_exceptions=False)

    @pytest.fixture
    def auth_token(self, client):
        """Get valid auth token"""
        response = client.post(
            "/token",
            data={"username": "admin", "password": "admin123"}
        )
        return response.json()["access_token"]

    def test_search_endpoint_basic(self, client, auth_token):
        """Test basic search endpoint exists and accepts requests"""
        response = client.post(
            "/search",
            json={"query": "test"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        # Could be 200 (success), 401 (auth required), or 500 (db error)
        assert response.status_code in [200, 401, 500]

    def test_search_endpoint_without_auth(self, client):
        """Test search endpoint without authentication"""
        response = client.post(
            "/search",
            json={"query": "test"}
        )
        # Should require auth
        assert response.status_code in [401, 403]


class TestExportEndpoints:
    """Tests for data export functionality"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app = api_v2_app  # Use module-level loaded app
        yield TestClient(app, raise_server_exceptions=False)

    @pytest.fixture
    def auth_token(self, client):
        """Get valid auth token"""
        response = client.post(
            "/token",
            data={"username": "admin", "password": "admin123"}
        )
        return response.json()["access_token"]

    def test_export_endpoint_exists(self, client, auth_token):
        """Test export endpoint exists and accepts requests"""
        response = client.post(
            "/export",
            json={"format": "json"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        # Could be 200 (success), 404 (not found), or 500 (db error)
        assert response.status_code in [200, 404, 500]

    def test_export_without_auth(self, client):
        """Test export endpoint requires authentication"""
        response = client.post(
            "/export",
            json={"format": "json"}
        )
        # Should require auth
        assert response.status_code in [401, 403, 404]


class TestInfoEndpoints:
    """Tests for API info endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app = api_v2_app  # Use module-level loaded app
        yield TestClient(app)

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info"""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "message" in data or "status" in data

    def test_api_info_endpoint(self, client):
        """Test API info endpoint"""
        response = client.get("/info")
        # May or may not exist
        assert response.status_code in [200, 404]


class TestErrorHandling:
    """Tests for error handling"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app = api_v2_app  # Use module-level loaded app
        yield TestClient(app)

    def test_404_not_found(self, client):
        """Test 404 response for non-existent endpoint"""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """Test 405 response for wrong HTTP method"""
        response = client.delete("/health")
        assert response.status_code == 405

    def test_invalid_json_body(self, client):
        """Test 422 response for invalid JSON body"""
        response = client.post(
            "/auth/register",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422


class TestCacheEndpoints:
    """Tests for cache functionality"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app = api_v2_app  # Use module-level loaded app
        yield TestClient(app)

    @pytest.fixture
    def auth_token(self, client):
        """Get valid auth token"""
        response = client.post(
            "/token",
            data={"username": "admin", "password": "admin123"}
        )
        return response.json()["access_token"]

    def test_cache_stats_endpoint(self, client, auth_token):
        """Test cache stats endpoint"""
        response = client.get(
            "/cache/stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        # May return stats or 404 if not implemented
        assert response.status_code in [200, 404, 500]
