
import sys
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

# MOCK THE DB MODULE BEFORE IMPORTING API_V2
# This prevents the "Failed to create database tables" error on import
mock_db = MagicMock()
mock_db.init_db = MagicMock()
mock_db.get_db = MagicMock()
mock_db.check_db_connection = MagicMock(return_value=True)
mock_db.SessionLocal = MagicMock()

# Patch both potential import paths
sys.modules['api.src.db'] = mock_db
sys.modules['db'] = mock_db

# Allow stripe_service import to work or be mocked
sys.modules['api.src.stripe_service'] = MagicMock()
from api.src import stripe_service as stripe_service_module
stripe_service_module.stripe_service = MagicMock()
stripe_service_module.stripe_service.get_price_id_for_tier.return_value = "price_mock"
stripe_service_module.stripe_service.create_checkout_session.return_value = {"url": "http://mock-checkout.com"}
stripe_service_module.stripe_service.create_portal_session.return_value = {"url": "http://mock-portal.com"}
stripe_service_module.stripe_service.create_customer.return_value = {"id": "cus_mock"}

# Now import app
from api.src.api_v2 import app, get_db_manager, get_current_user

client = TestClient(app)

# Mock user dependency
def mock_get_current_user():
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "roles": ["user"],
        "subscription_tier": "free",
        "stripe_customer_id": "cus_existing"
    }

# Mock database manager
class MockDBManager:
    def get_user_by_username(self, username):
        if username == "testuser":
            return {
                "id": 1,
                "username": "testuser",
                "email": "test@example.com",
                "full_name": "Test User",
                "stripe_customer_id": "cus_existing",
                "subscription_tier": "free"
            }
        return None

    def update_user(self, user_id, **kwargs):
        return True

def test_create_checkout_session():
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_db_manager] = lambda: MockDBManager()
    
    # We need to ensure stripe_service usage in api_v2 uses our mock
    # The import in api_v2 is: from stripe_service import stripe_service
    # We patched usage via sys.modules above, but api_v2 might have imported it already if cached?
    # No, we set sys.modules before import.
    
    response = client.post("/subscription/checkout?tier=pro")
    
    assert response.status_code == 200
    assert response.json() == {"checkout_url": "http://mock-checkout.com"}

def test_create_portal_session():
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_db_manager] = lambda: MockDBManager()

    response = client.post("/subscription/portal")
    
    assert response.status_code == 200
    assert response.json() == {"portal_url": "http://mock-portal.com"}

