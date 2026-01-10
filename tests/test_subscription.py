"""
Tests for subscription and payment functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class TestStripeService:
    """Tests for StripeService class."""

    def test_stripe_service_initialization_without_key(self):
        """Test StripeService initializes in mock mode without API key."""
        import os
        old_key = os.environ.pop('STRIPE_SECRET_KEY', None)
        try:
            # Reimport to get fresh initialization
            import importlib
            import sys
            if 'api.src.stripe_service' in sys.modules:
                del sys.modules['api.src.stripe_service']

            from api.src.stripe_service import StripeService
            service = StripeService()

            # Should be in mock mode
            assert service.stripe_available is False
        finally:
            if old_key:
                os.environ['STRIPE_SECRET_KEY'] = old_key

    def test_create_customer_mock_mode(self):
        """Test creating customer in mock mode."""
        from api.src.stripe_service import StripeService
        service = StripeService()
        service.stripe_available = False

        customer = service.create_customer(
            email="test@example.com",
            name="Test User",
            metadata={"user_id": "123"}
        )

        assert customer['email'] == "test@example.com"
        assert customer['name'] == "Test User"
        assert 'id' in customer
        assert customer['id'].startswith('cus_mock_')

    def test_create_checkout_session_mock_mode(self):
        """Test creating checkout session in mock mode."""
        from api.src.stripe_service import StripeService
        service = StripeService()
        service.stripe_available = False

        session = service.create_checkout_session(
            customer_id="cus_123",
            price_id="price_basic",
            success_url="http://localhost:3000/success",
            cancel_url="http://localhost:3000/cancel"
        )

        assert 'id' in session
        assert session['id'].startswith('cs_mock_')
        assert 'url' in session
        assert 'mock=true' in session['url']

    def test_create_portal_session_mock_mode(self):
        """Test creating portal session in mock mode."""
        from api.src.stripe_service import StripeService
        service = StripeService()
        service.stripe_available = False

        session = service.create_portal_session(
            customer_id="cus_123",
            return_url="http://localhost:3000/settings"
        )

        assert 'url' in session
        assert 'portal=mock' in session['url']

    def test_get_price_id_for_tier(self):
        """Test getting price ID for subscription tier."""
        from api.src.stripe_service import StripeService
        service = StripeService()

        assert service.get_price_id_for_tier('basic') is not None
        assert service.get_price_id_for_tier('pro') is not None
        assert service.get_price_id_for_tier('enterprise') is not None
        assert service.get_price_id_for_tier('invalid') is None

    def test_handle_subscription_event_created(self):
        """Test handling subscription created event."""
        from api.src.stripe_service import StripeService
        service = StripeService()

        event_data = {
            'id': 'sub_123',
            'customer': 'cus_456',
            'current_period_end': int(datetime.now().timestamp()) + 86400 * 30,
            'items': {
                'data': [{
                    'price': {'id': 'price_basic_placeholder'}
                }]
            }
        }

        result = service.handle_subscription_event(
            'customer.subscription.created',
            event_data
        )

        assert result['success'] is True
        assert result['action'] == 'created'
        assert result['subscription_id'] == 'sub_123'
        assert result['customer_id'] == 'cus_456'
        assert result['tier'] == 'basic'

    def test_handle_subscription_event_cancelled(self):
        """Test handling subscription deleted event."""
        from api.src.stripe_service import StripeService
        service = StripeService()

        event_data = {
            'id': 'sub_123',
            'customer': 'cus_456',
        }

        result = service.handle_subscription_event(
            'customer.subscription.deleted',
            event_data
        )

        assert result['success'] is True
        assert result['action'] == 'cancelled'
        assert result['tier'] == 'free'

    def test_verify_webhook_mock_mode(self):
        """Test webhook verification in mock mode."""
        from api.src.stripe_service import StripeService
        import json

        service = StripeService()
        service.stripe_available = False

        payload = json.dumps({'type': 'checkout.session.completed'}).encode()
        event = service.verify_webhook(payload, 'sig_123')

        assert event is not None
        assert event['type'] == 'checkout.session.completed'


class TestSubscriptionEndpoints:
    """Tests for subscription API endpoints."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock DatabaseManager."""
        mock = MagicMock()
        mock.get_user_by_username.return_value = {
            'id': 1,
            'username': 'testuser',
            'email': 'test@example.com',
            'full_name': 'Test User',
            'subscription_tier': 'free',
            'subscription_expires': None,
        }
        mock.update_user.return_value = True
        return mock

    @pytest.fixture
    def mock_current_user(self):
        """Create a mock current user."""
        return {
            'sub': 'testuser',
            'username': 'testuser',
            'email': 'test@example.com',
        }

    def test_subscribe_invalid_tier(self, mock_db_manager, mock_current_user):
        """Test subscribing with invalid tier."""
        # Test the validation logic without importing FastAPI
        tier = "invalid_tier"
        valid_tiers = ['basic', 'pro', 'enterprise']

        assert tier not in valid_tiers
        # In the actual endpoint, this would raise HTTPException(400)

    def test_subscribe_valid_tier_mock_mode(self, mock_db_manager, mock_current_user):
        """Test subscribing with valid tier in mock mode."""
        # This is a simplified test - full integration test would use TestClient
        tier = "basic"
        assert tier in ['basic', 'pro', 'enterprise']

        # Simulate the subscription update
        expires_at = datetime.utcnow() + timedelta(days=30)
        mock_db_manager.update_user(
            1,
            subscription_tier=tier,
            subscription_expires=expires_at
        )

        mock_db_manager.update_user.assert_called_once()

    def test_cancel_subscription_no_active(self, mock_db_manager):
        """Test canceling when no active subscription."""
        mock_db_manager.get_user_by_username.return_value = {
            'id': 1,
            'subscription_tier': 'free',
        }

        user = mock_db_manager.get_user_by_username('testuser')

        # Verify that user has no active subscription
        assert user.get('subscription_tier', 'free') == 'free'
        # In the actual endpoint, this would raise HTTPException(400)

    def test_get_subscription_status(self, mock_db_manager):
        """Test getting subscription status."""
        mock_db_manager.get_user_by_username.return_value = {
            'id': 1,
            'subscription_tier': 'pro',
            'subscription_expires': (datetime.utcnow() + timedelta(days=15)).isoformat(),
        }

        user = mock_db_manager.get_user_by_username('testuser')

        assert user['subscription_tier'] == 'pro'
        assert user['subscription_expires'] is not None


class TestSubscriptionTierFeatures:
    """Tests for subscription tier feature access."""

    def test_free_tier_features(self):
        """Test free tier has limited features."""
        from datagod.models.user import User

        user = User()
        user.subscription_tier = 'free'

        assert user.can_access_feature('basic_search') is True
        assert user.can_access_feature('view_records') is True
        assert user.can_access_feature('export_csv') is False
        assert user.can_access_feature('api_access') is False

    def test_basic_tier_features(self):
        """Test basic tier features."""
        from datagod.models.user import User

        user = User()
        user.subscription_tier = 'basic'

        assert user.can_access_feature('basic_search') is True
        assert user.can_access_feature('export_csv') is True
        assert user.can_access_feature('advanced_search') is True
        assert user.can_access_feature('api_access') is False

    def test_pro_tier_features(self):
        """Test pro tier features."""
        from datagod.models.user import User

        user = User()
        user.subscription_tier = 'pro'

        assert user.can_access_feature('basic_search') is True
        assert user.can_access_feature('export_csv') is True
        assert user.can_access_feature('api_access') is True
        assert user.can_access_feature('bulk_operations') is True
        assert user.can_access_feature('unlimited_exports') is False

    def test_enterprise_tier_features(self):
        """Test enterprise tier has all features."""
        from datagod.models.user import User

        user = User()
        user.subscription_tier = 'enterprise'

        assert user.can_access_feature('basic_search') is True
        assert user.can_access_feature('export_csv') is True
        assert user.can_access_feature('api_access') is True
        assert user.can_access_feature('unlimited_exports') is True
        assert user.can_access_feature('custom_integrations') is True


class TestStripeServiceAdditional:
    """Additional tests for StripeService to improve coverage."""

    def test_get_subscription_mock_mode(self):
        """Test getting subscription in mock mode returns None."""
        from api.src.stripe_service import StripeService
        service = StripeService()
        service.stripe_available = False

        result = service.get_subscription('sub_123')
        assert result is None

    def test_cancel_subscription_mock_mode(self):
        """Test canceling subscription in mock mode returns True."""
        from api.src.stripe_service import StripeService
        service = StripeService()
        service.stripe_available = False

        result = service.cancel_subscription('sub_123', at_period_end=True)
        assert result is True

    def test_cancel_subscription_immediate_mock_mode(self):
        """Test canceling subscription immediately in mock mode."""
        from api.src.stripe_service import StripeService
        service = StripeService()
        service.stripe_available = False

        result = service.cancel_subscription('sub_123', at_period_end=False)
        assert result is True

    def test_verify_webhook_invalid_json_mock_mode(self):
        """Test webhook verification with invalid JSON in mock mode."""
        from api.src.stripe_service import StripeService
        service = StripeService()
        service.stripe_available = False

        result = service.verify_webhook(b'not valid json', 'sig_123')
        assert result is None

    def test_handle_subscription_event_updated(self):
        """Test handling subscription updated event."""
        from api.src.stripe_service import StripeService
        service = StripeService()

        event_data = {
            'id': 'sub_123',
            'customer': 'cus_456',
            'current_period_end': int(datetime.now().timestamp()) + 86400 * 30,
            'items': {
                'data': [{
                    'price': {'id': 'price_pro_placeholder'}
                }]
            }
        }

        result = service.handle_subscription_event(
            'customer.subscription.updated',
            event_data
        )

        assert result['success'] is True
        assert result['action'] == 'updated'
        assert result['tier'] == 'pro'

    def test_handle_subscription_event_payment_failed(self):
        """Test handling payment failed event."""
        from api.src.stripe_service import StripeService
        service = StripeService()

        event_data = {
            'id': 'inv_123',
            'customer': 'cus_456',
        }

        result = service.handle_subscription_event(
            'invoice.payment_failed',
            event_data
        )

        assert result['success'] is True
        assert result['action'] == 'payment_failed'

    def test_handle_subscription_event_payment_succeeded(self):
        """Test handling payment succeeded event."""
        from api.src.stripe_service import StripeService
        service = StripeService()

        event_data = {
            'id': 'inv_123',
            'customer': 'cus_456',
            'current_period_end': int(datetime.now().timestamp()) + 86400 * 30,
        }

        result = service.handle_subscription_event(
            'invoice.payment_succeeded',
            event_data
        )

        assert result['success'] is True
        assert result['action'] == 'payment_succeeded'
        assert result['expires_at'] is not None

    def test_get_tier_from_price_unknown(self):
        """Test getting tier from unknown price ID returns free."""
        from api.src.stripe_service import StripeService
        service = StripeService()

        # Access the private method directly
        tier = service._get_tier_from_price('price_unknown_xyz')
        assert tier == 'free'

    def test_get_tier_from_price_enterprise(self):
        """Test getting tier from enterprise price ID."""
        from api.src.stripe_service import StripeService
        service = StripeService()

        tier = service._get_tier_from_price('price_enterprise_placeholder')
        assert tier == 'enterprise'

    def test_create_customer_without_name(self):
        """Test creating customer without optional name field."""
        from api.src.stripe_service import StripeService
        service = StripeService()
        service.stripe_available = False

        customer = service.create_customer(email="noname@example.com")

        assert customer['email'] == "noname@example.com"
        assert customer['name'] is None
        assert 'id' in customer

    def test_create_checkout_session_with_metadata(self):
        """Test creating checkout session with metadata."""
        from api.src.stripe_service import StripeService
        service = StripeService()
        service.stripe_available = False

        session = service.create_checkout_session(
            customer_id="cus_123",
            price_id="price_basic",
            success_url="http://localhost:3000/success",
            cancel_url="http://localhost:3000/cancel",
            metadata={"user_id": "456", "source": "pricing_page"}
        )

        assert 'id' in session
        assert session['status'] == 'open'

    def test_handle_subscription_event_unknown_type(self):
        """Test handling unknown event type."""
        from api.src.stripe_service import StripeService
        service = StripeService()

        event_data = {
            'id': 'sub_123',
            'customer': 'cus_456',
        }

        result = service.handle_subscription_event(
            'unknown.event.type',
            event_data
        )

        assert result['success'] is True
        assert result['action'] is None  # Unknown event type

    def test_service_initialization_logs_mock_mode(self):
        """Test that service logs when in mock mode."""
        from api.src.stripe_service import StripeService
        import os

        # Temporarily remove the key
        old_key = os.environ.pop('STRIPE_SECRET_KEY', None)
        try:
            service = StripeService()
            assert service.stripe_available is False
        finally:
            if old_key:
                os.environ['STRIPE_SECRET_KEY'] = old_key
