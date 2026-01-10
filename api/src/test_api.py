import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from passlib.context import CryptContext
import sys
from pathlib import Path
import importlib.util

# Add paths for imports
api_src_path = Path(__file__).parent
project_root = api_src_path.parent.parent
sys.path.insert(0, str(api_src_path))
sys.path.insert(1, str(project_root))

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
            }
        }

    def get_user_by_username(self, username):
        return self.demo_users.get(username)

    def get_user_for_auth(self, username):
        return self.demo_users.get(username)

    def check_user_locked(self, username):
        return False

    def record_login(self, username, success=True):
        return True

    def init_database(self):
        return True


def create_mock_user_db_manager():
    """Create a mock user database manager with demo users."""
    return MockUserDbManager()


# Load api_v2_simple module directly to set up mock before main.py imports it
api_v2_spec = importlib.util.spec_from_file_location("api_v2_simple", api_src_path / "api_v2_simple.py")
api_v2_module = importlib.util.module_from_spec(api_v2_spec)
sys.modules["api_v2_simple"] = api_v2_module
api_v2_spec.loader.exec_module(api_v2_module)

# Now we can access the functions and set the mock
set_user_db_manager = api_v2_module.set_user_db_manager

# Create and set mock user db manager BEFORE importing main_app
mock_user_db = create_mock_user_db_manager()
set_user_db_manager(mock_user_db)

# Now load main module
main_spec = importlib.util.spec_from_file_location("main", api_src_path / "main.py")
main_module = importlib.util.module_from_spec(main_spec)
sys.modules["main"] = main_module
main_spec.loader.exec_module(main_module)

main_app = main_module.main_app

# Create test client
client = TestClient(main_app)


class TestAPI(unittest.TestCase):

    def test_root_endpoint(self):
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json())

    def test_health_endpoint(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertIn("status", response.json())

    def test_token_endpoint(self):
        # Test token endpoint with valid admin credentials (api v2 is mounted at /api/v2)
        response = client.post("/api/v2/token",
                               data={"username": "admin", "password": "admin123"})
        # This should return 200 with valid credentials
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.json())

    def test_token_endpoint_invalid_credentials(self):
        # Test token endpoint with invalid credentials
        response = client.post("/api/v2/token",
                               data={"username": "invalid_user", "password": "invalid_password"})
        # Should return 401 Unauthorized
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
