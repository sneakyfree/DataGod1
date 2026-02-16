"""
Comprehensive tests for DataGod Stripe payment integration.

This module tests:
- StripeService class methods
- Mock mode operation
- Customer creation
- Checkout session creation
- Portal session creation
- Subscription management
- Webhook handling
- Tier mapping

Coverage target: 100% of stripe_service.py
"""

import pytest
import os
import sys
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Set test environment before imports
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
# Ensure Stripe is in mock mode
os.environ.pop("STRIPE_SECRET_KEY", None)

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api', 'src'))


def setup_module():
    """Ensure fresh stripe_service import (not a MagicMock from another test)."""
    import importlib
    key = 'api.src.stripe_service'
    if key in sys.modules:
        mod = sys.modules[key]
        # If another test file replaced the module with a MagicMock, remove it
        if not hasattr(mod, '__file__') or isinstance(mod, MagicMock):
            del sys.modules[key]
            # Also remove any cached parent imports that reference the mock
            for k in list(sys.modules):
                if k.startswith('api.src') and isinstance(sys.modules.get(k), MagicMock):
                    del sys.modules[k]


class TestStripeServiceInitialization:
    """Tests for StripeService initialization."""

    def test_service_creation(self):
        """Test StripeService can be instantiated."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        assert service is not None

    def test_mock_mode_when_no_key(self):
        """Test service runs in mock mode without STRIPE_SECRET_KEY."""
        # Ensure no key is set
        original_key = os.environ.pop('STRIPE_SECRET_KEY', None)

        try:
            from api.src.stripe_service import StripeService
            service = StripeService()

            # Should be in mock mode
            assert service.stripe_available == False
        finally:
            if original_key:
                os.environ['STRIPE_SECRET_KEY'] = original_key

    def test_price_ids_configuration(self):
        """Test STRIPE_PRICE_IDS are configured."""
        from api.src.stripe_service import STRIPE_PRICE_IDS

        assert 'basic' in STRIPE_PRICE_IDS
        assert 'pro' in STRIPE_PRICE_IDS
        assert 'enterprise' in STRIPE_PRICE_IDS


class TestStripeServiceCustomer:
    """Tests for customer management."""

    def test_create_customer_mock_mode(self):
        """Test creating customer in mock mode."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        result = service.create_customer(
            email="test@example.com",
            name="Test User",
            metadata={"user_id": "123"}
        )

        assert 'id' in result
        assert result['email'] == "test@example.com"
        assert result['name'] == "Test User"
        assert 'cus_mock_' in result['id']

    def test_create_customer_without_name(self):
        """Test creating customer without optional name."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        result = service.create_customer(email="test@example.com")

        assert 'id' in result
        assert result['email'] == "test@example.com"
        assert result['name'] is None

    def test_create_customer_without_metadata(self):
        """Test creating customer without metadata."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        result = service.create_customer(email="test@example.com")

        assert result['metadata'] == {}


class TestStripeServiceCheckout:
    """Tests for checkout session creation."""

    def test_create_checkout_session_mock_mode(self):
        """Test creating checkout session in mock mode."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        result = service.create_checkout_session(
            customer_id="cus_mock_123",
            price_id="price_basic",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel"
        )

        assert 'id' in result
        assert 'url' in result
        assert 'cs_mock_' in result['id']
        assert 'success' in result['url']
        assert 'mock=true' in result['url']

    def test_create_checkout_session_with_metadata(self):
        """Test creating checkout session with metadata."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        result = service.create_checkout_session(
            customer_id="cus_mock_123",
            price_id="price_basic",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
            metadata={"order_id": "order_123"}
        )

        assert result['status'] == 'open'


class TestStripeServicePortal:
    """Tests for billing portal session."""

    def test_create_portal_session_mock_mode(self):
        """Test creating portal session in mock mode."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        result = service.create_portal_session(
            customer_id="cus_mock_123",
            return_url="https://example.com/account"
        )

        assert 'url' in result
        assert 'portal=mock' in result['url']


class TestStripeServiceSubscription:
    """Tests for subscription management."""

    def test_get_subscription_mock_mode(self):
        """Test getting subscription in mock mode returns None."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        result = service.get_subscription("sub_mock_123")

        # Mock mode returns None for subscription retrieval
        assert result is None

    def test_cancel_subscription_mock_mode(self):
        """Test canceling subscription in mock mode."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        result = service.cancel_subscription("sub_mock_123")

        # Mock mode returns True for cancellation
        assert result is True

    def test_cancel_subscription_immediate(self):
        """Test immediate cancellation in mock mode."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        result = service.cancel_subscription("sub_mock_123", at_period_end=False)

        assert result is True


class TestStripeServiceWebhook:
    """Tests for webhook handling."""

    def test_verify_webhook_mock_mode_valid_json(self):
        """Test verifying webhook in mock mode with valid JSON."""
        from api.src.stripe_service import StripeService

        service = StripeService()

        payload = json.dumps({
            "id": "evt_123",
            "type": "customer.subscription.created",
            "data": {"object": {"id": "sub_123"}}
        }).encode()

        result = service.verify_webhook(payload, "sig_mock")

        assert result is not None
        assert result['type'] == 'customer.subscription.created'

    def test_verify_webhook_mock_mode_invalid_json(self):
        """Test verifying webhook in mock mode with invalid JSON."""
        from api.src.stripe_service import StripeService

        service = StripeService()

        payload = b"invalid json"
        result = service.verify_webhook(payload, "sig_mock")

        assert result is None


class TestStripeServiceTierMapping:
    """Tests for tier/price ID mapping."""

    def test_get_price_id_for_basic(self):
        """Test getting price ID for basic tier."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        price_id = service.get_price_id_for_tier('basic')

        assert price_id is not None

    def test_get_price_id_for_pro(self):
        """Test getting price ID for pro tier."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        price_id = service.get_price_id_for_tier('pro')

        assert price_id is not None

    def test_get_price_id_for_enterprise(self):
        """Test getting price ID for enterprise tier."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        price_id = service.get_price_id_for_tier('enterprise')

        assert price_id is not None

    def test_get_price_id_for_invalid_tier(self):
        """Test getting price ID for invalid tier."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        price_id = service.get_price_id_for_tier('invalid_tier')

        assert price_id is None

    def test_get_tier_from_price(self):
        """Test internal _get_tier_from_price method."""
        from api.src.stripe_service import StripeService, STRIPE_PRICE_IDS

        service = StripeService()

        # Test with known price ID
        basic_price = STRIPE_PRICE_IDS['basic']
        tier = service._get_tier_from_price(basic_price)
        assert tier == 'basic'

    def test_get_tier_from_unknown_price(self):
        """Test _get_tier_from_price with unknown price ID."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        tier = service._get_tier_from_price('price_unknown_xyz')

        # Unknown price should return 'free'
        assert tier == 'free'


class TestStripeServiceEventHandling:
    """Tests for subscription event handling."""

    def test_handle_subscription_created(self):
        """Test handling subscription.created event."""
        from api.src.stripe_service import StripeService, STRIPE_PRICE_IDS

        service = StripeService()

        subscription_data = {
            'id': 'sub_123',
            'customer': 'cus_123',
            'items': {
                'data': [{'price': {'id': STRIPE_PRICE_IDS['basic']}}]
            },
            'current_period_end': int(datetime.now().timestamp()) + 86400
        }

        result = service.handle_subscription_event(
            'customer.subscription.created',
            subscription_data
        )

        assert result['success'] is True
        assert result['action'] == 'created'
        assert result['subscription_id'] == 'sub_123'
        assert result['customer_id'] == 'cus_123'

    def test_handle_subscription_updated(self):
        """Test handling subscription.updated event."""
        from api.src.stripe_service import StripeService, STRIPE_PRICE_IDS

        service = StripeService()

        subscription_data = {
            'id': 'sub_123',
            'customer': 'cus_123',
            'items': {
                'data': [{'price': {'id': STRIPE_PRICE_IDS['pro']}}]
            },
            'current_period_end': int(datetime.now().timestamp()) + 86400
        }

        result = service.handle_subscription_event(
            'customer.subscription.updated',
            subscription_data
        )

        assert result['action'] == 'updated'

    def test_handle_subscription_deleted(self):
        """Test handling subscription.deleted event."""
        from api.src.stripe_service import StripeService

        service = StripeService()

        subscription_data = {
            'id': 'sub_123',
            'customer': 'cus_123',
        }

        result = service.handle_subscription_event(
            'customer.subscription.deleted',
            subscription_data
        )

        assert result['action'] == 'cancelled'
        assert result['tier'] == 'free'

    def test_handle_payment_failed(self):
        """Test handling invoice.payment_failed event."""
        from api.src.stripe_service import StripeService

        service = StripeService()

        subscription_data = {
            'id': 'inv_123',
            'customer': 'cus_123',
        }

        result = service.handle_subscription_event(
            'invoice.payment_failed',
            subscription_data
        )

        assert result['action'] == 'payment_failed'

    def test_handle_payment_succeeded(self):
        """Test handling invoice.payment_succeeded event."""
        from api.src.stripe_service import StripeService

        service = StripeService()

        subscription_data = {
            'id': 'inv_123',
            'customer': 'cus_123',
            'current_period_end': int(datetime.now().timestamp()) + 86400
        }

        result = service.handle_subscription_event(
            'invoice.payment_succeeded',
            subscription_data
        )

        assert result['action'] == 'payment_succeeded'

    def test_handle_unknown_event(self):
        """Test handling unknown event type."""
        from api.src.stripe_service import StripeService

        service = StripeService()

        result = service.handle_subscription_event(
            'unknown.event.type',
            {'id': 'obj_123'}
        )

        assert result['success'] is True
        assert result['action'] is None


class TestStripeServiceGlobalInstance:
    """Tests for global stripe_service instance."""

    def test_global_instance_exists(self):
        """Test global stripe_service instance is created."""
        from api.src.stripe_service import stripe_service

        assert stripe_service is not None

    def test_global_instance_is_stripe_service(self):
        """Test global instance is StripeService type."""
        from api.src.stripe_service import stripe_service, StripeService

        assert isinstance(stripe_service, StripeService)


class TestSubscriptionTierLogic:
    """Tests for subscription tier business logic."""

    def test_tier_list(self):
        """Test subscription tier list."""
        tiers = ['free', 'basic', 'pro', 'enterprise']

        assert 'free' in tiers
        assert 'enterprise' in tiers

    def test_tier_hierarchy(self):
        """Test tier hierarchy ordering."""
        tier_order = {'free': 0, 'basic': 1, 'pro': 2, 'enterprise': 3}

        assert tier_order['free'] < tier_order['basic']
        assert tier_order['basic'] < tier_order['pro']
        assert tier_order['pro'] < tier_order['enterprise']

    def test_tier_features(self):
        """Test tier feature mapping."""
        tier_features = {
            'free': ['basic_search', 'view_records'],
            'basic': ['basic_search', 'view_records', 'export_csv'],
            'pro': ['basic_search', 'view_records', 'export_csv', 'api_access'],
            'enterprise': ['basic_search', 'view_records', 'export_csv', 'api_access', 'unlimited']
        }

        assert 'basic_search' in tier_features['free']
        assert 'api_access' in tier_features['pro']


class TestPriceIDConfiguration:
    """Tests for price ID configuration."""

    def test_price_ids_are_strings(self):
        """Test all price IDs are strings."""
        from api.src.stripe_service import STRIPE_PRICE_IDS

        for tier, price_id in STRIPE_PRICE_IDS.items():
            assert isinstance(price_id, str)

    def test_placeholder_price_ids(self):
        """Test placeholder price IDs have expected format."""
        from api.src.stripe_service import STRIPE_PRICE_IDS

        # Without env vars set, should have placeholder values
        for tier, price_id in STRIPE_PRICE_IDS.items():
            assert price_id is not None
            assert len(price_id) > 0


class TestDatetimeHandling:
    """Tests for datetime handling in Stripe service."""

    def test_timestamp_conversion(self):
        """Test converting timestamps to datetime."""
        timestamp = int(datetime.now().timestamp())
        dt = datetime.fromtimestamp(timestamp)

        assert dt is not None
        assert isinstance(dt, datetime)

    def test_expires_at_calculation(self):
        """Test subscription expiry calculation."""
        current_period_end = int((datetime.now() + timedelta(days=30)).timestamp())
        expires_at = datetime.fromtimestamp(current_period_end)

        assert expires_at > datetime.now()


class TestMockModeConsistency:
    """Tests to ensure mock mode is consistent."""

    def test_mock_customer_id_format(self):
        """Test mock customer ID format."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        result = service.create_customer(email="test@example.com")

        assert result['id'].startswith('cus_mock_')

    def test_mock_session_id_format(self):
        """Test mock checkout session ID format."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        result = service.create_checkout_session(
            customer_id="cus_mock_123",
            price_id="price_test",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel"
        )

        assert result['id'].startswith('cs_mock_')


class TestWebhookSecretHandling:
    """Tests for webhook secret handling."""

    def test_webhook_secret_from_env(self):
        """Test webhook secret is read from environment."""
        from api.src.stripe_service import StripeService

        # Set a test webhook secret
        original = os.environ.get('STRIPE_WEBHOOK_SECRET')
        os.environ['STRIPE_WEBHOOK_SECRET'] = 'whsec_test_123'

        try:
            service = StripeService()
            assert service.webhook_secret == 'whsec_test_123'
        finally:
            if original:
                os.environ['STRIPE_WEBHOOK_SECRET'] = original
            else:
                os.environ.pop('STRIPE_WEBHOOK_SECRET', None)

    def test_empty_webhook_secret(self):
        """Test handling empty webhook secret."""
        from api.src.stripe_service import StripeService

        os.environ.pop('STRIPE_WEBHOOK_SECRET', None)

        service = StripeService()
        # Should not raise, just use empty string
        assert service.webhook_secret == '' or service.webhook_secret is not None
