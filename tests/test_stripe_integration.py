"""
Tests for Stripe subscription endpoints in api_v2.
Uses proper function-level mocking to avoid sys.modules pollution.
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Ensure test environment
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"


def _get_app_and_client():
    """Import app with mocked DB to avoid database initialization errors."""
    # Mock the DB module if not already loaded with real module
    mock_db = MagicMock()
    mock_db.init_db = MagicMock()
    mock_db.get_db = MagicMock()
    mock_db.check_db_connection = MagicMock(return_value=True)
    mock_db.SessionLocal = MagicMock()

    saved = {}
    keys_to_patch = ['api.src.db', 'db']
    for k in keys_to_patch:
        saved[k] = sys.modules.get(k)
        if k not in sys.modules or isinstance(sys.modules[k], MagicMock):
            sys.modules[k] = mock_db

    from api.src.api_v2 import app, get_db_manager, get_current_user
    from fastapi.testclient import TestClient

    # Restore patched modules
    for k in keys_to_patch:
        if saved[k] is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = saved[k]

    return app, TestClient(app), get_db_manager, get_current_user


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
    app, client, get_db_manager, get_current_user = _get_app_and_client()
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_db_manager] = lambda: MockDBManager()

    # Mock the stripe_service at the module level where api_v2 uses it
    mock_stripe = MagicMock()
    mock_stripe.get_price_id_for_tier.return_value = "price_mock"
    mock_stripe.create_checkout_session.return_value = {"url": "http://mock-checkout.com"}

    with patch("api.src.api_v2.stripe_service", mock_stripe):
        response = client.post("/subscription/checkout?tier=pro")

    assert response.status_code == 200
    assert response.json() == {"checkout_url": "http://mock-checkout.com"}

    app.dependency_overrides.clear()


def test_create_portal_session():
    app, client, get_db_manager, get_current_user = _get_app_and_client()
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_db_manager] = lambda: MockDBManager()

    mock_stripe = MagicMock()
    mock_stripe.create_portal_session.return_value = {"url": "http://mock-portal.com"}

    with patch("api.src.api_v2.stripe_service", mock_stripe):
        response = client.post("/subscription/portal")

    assert response.status_code == 200
    assert response.json() == {"portal_url": "http://mock-portal.com"}

    app.dependency_overrides.clear()
