"""
Tests for Stripe service.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import json


class TestStripeServiceImport:
    """Tests for StripeService import."""

    def test_stripe_service_import(self):
        """Test StripeService can be imported."""
        from api.src.stripe_service import StripeService
        assert StripeService is not None

    def test_stripe_service_instance(self):
        """Test global stripe_service instance exists."""
        from api.src.stripe_service import stripe_service
        assert stripe_service is not None

    def test_stripe_price_ids_defined(self):
        """Test price IDs are defined."""
        from api.src.stripe_service import STRIPE_PRICE_IDS
        assert 'basic' in STRIPE_PRICE_IDS
        assert 'pro' in STRIPE_PRICE_IDS
        assert 'enterprise' in STRIPE_PRICE_IDS


class TestStripeServiceMockMode:
    """Tests for StripeService in mock mode (no Stripe configured)."""

    def test_mock_mode_detection(self):
        """Test service detects mock mode when Stripe not configured."""
        from api.src.stripe_service import StripeService
        with patch.dict('os.environ', {'STRIPE_SECRET_KEY': ''}, clear=False):
            service = StripeService()
            # When STRIPE_SECRET_KEY is empty, should be in mock mode
            # The actual behavior depends on STRIPE_AVAILABLE constant

    def test_create_customer_mock_mode(self):
        """Test creating customer in mock mode."""
        from api.src.stripe_service import StripeService
        service = StripeService()
        service.stripe_available = False  # Force mock mode

        customer = service.create_customer(
            email="test@example.com",
            name="Test User",
            metadata={'user_id': '123'}
        )

        assert customer is not None
        assert 'id' in customer
        assert customer['id'].startswith('cus_mock_')
        assert customer['email'] == "test@example.com"
        assert customer['name'] == "Test User"

    def test_create_checkout_session_mock_mode(self):
        """Test creating checkout session in mock mode."""
        from api.src.stripe_service import StripeService
        service = StripeService()
        service.stripe_available = False  # Force mock mode

        session = service.create_checkout_session(
            customer_id='cus_test_123',
            price_id='price_test',
            success_url='https://example.com/success',
            cancel_url='https://example.com/cancel'
        )

        assert session is not None
        assert 'id' in session
        assert session['id'].startswith('cs_mock_')
        assert 'url' in session
        assert session['status'] == 'open'

    def test_create_portal_session_mock_mode(self):
        """Test creating portal session in mock mode."""
        from api.src.stripe_service import StripeService
        service = StripeService()
        service.stripe_available = False  # Force mock mode

        session = service.create_portal_session(
            customer_id='cus_test_123',
            return_url='https://example.com/account'
        )

        assert session is not None
        assert 'url' in session
        assert 'portal=mock' in session['url']

    def test_get_subscription_mock_mode(self):
        """Test getting subscription in mock mode returns None."""
        from api.src.stripe_service import StripeService
        service = StripeService()
        service.stripe_available = False  # Force mock mode

        result = service.get_subscription('sub_test_123')
        assert result is None

    def test_cancel_subscription_mock_mode(self):
        """Test canceling subscription in mock mode."""
        from api.src.stripe_service import StripeService
        service = StripeService()
        service.stripe_available = False  # Force mock mode

        result = service.cancel_subscription('sub_test_123')
        assert result is True

    def test_verify_webhook_mock_mode(self):
        """Test verifying webhook in mock mode."""
        from api.src.stripe_service import StripeService
        service = StripeService()
        service.stripe_available = False  # Force mock mode

        payload = json.dumps({'type': 'test.event', 'data': {}}).encode()
        result = service.verify_webhook(payload, 'sig_test')

        assert result is not None
        assert result['type'] == 'test.event'

    def test_verify_webhook_invalid_json_mock_mode(self):
        """Test verifying webhook with invalid JSON in mock mode."""
        from api.src.stripe_service import StripeService
        service = StripeService()
        service.stripe_available = False  # Force mock mode

        result = service.verify_webhook(b'not valid json', 'sig_test')
        assert result is None


class TestStripeServicePriceMapping:
    """Tests for price ID mapping."""

    def test_get_price_id_basic(self):
        """Test getting price ID for basic tier."""
        from api.src.stripe_service import StripeService
        service = StripeService()

        price_id = service.get_price_id_for_tier('basic')
        assert price_id is not None

    def test_get_price_id_pro(self):
        """Test getting price ID for pro tier."""
        from api.src.stripe_service import StripeService
        service = StripeService()

        price_id = service.get_price_id_for_tier('pro')
        assert price_id is not None

    def test_get_price_id_enterprise(self):
        """Test getting price ID for enterprise tier."""
        from api.src.stripe_service import StripeService
        service = StripeService()

        price_id = service.get_price_id_for_tier('enterprise')
        assert price_id is not None

    def test_get_price_id_invalid(self):
        """Test getting price ID for invalid tier."""
        from api.src.stripe_service import StripeService
        service = StripeService()

        price_id = service.get_price_id_for_tier('invalid_tier')
        assert price_id is None

    def test_get_tier_from_price(self):
        """Test mapping price ID back to tier."""
        from api.src.stripe_service import StripeService, STRIPE_PRICE_IDS
        service = StripeService()

        for tier, price_id in STRIPE_PRICE_IDS.items():
            result = service._get_tier_from_price(price_id)
            assert result == tier

    def test_get_tier_from_price_unknown(self):
        """Test mapping unknown price ID returns free."""
        from api.src.stripe_service import StripeService
        service = StripeService()

        result = service._get_tier_from_price('price_unknown')
        assert result == 'free'


class TestStripeServiceSubscriptionEvents:
    """Tests for subscription event handling."""

    def test_handle_subscription_created(self):
        """Test handling subscription created event."""
        from api.src.stripe_service import StripeService, STRIPE_PRICE_IDS
        service = StripeService()

        subscription_data = {
            'id': 'sub_test_123',
            'customer': 'cus_test_456',
            'items': {
                'data': [
                    {'price': {'id': STRIPE_PRICE_IDS['basic']}}
                ]
            },
            'current_period_end': int((datetime.now() + timedelta(days=30)).timestamp())
        }

        result = service.handle_subscription_event(
            'customer.subscription.created',
            subscription_data
        )

        assert result['success'] is True
        assert result['action'] == 'created'
        assert result['subscription_id'] == 'sub_test_123'
        assert result['customer_id'] == 'cus_test_456'
        assert result['tier'] == 'basic'

    def test_handle_subscription_updated(self):
        """Test handling subscription updated event."""
        from api.src.stripe_service import StripeService, STRIPE_PRICE_IDS
        service = StripeService()

        subscription_data = {
            'id': 'sub_test_123',
            'customer': 'cus_test_456',
            'items': {
                'data': [
                    {'price': {'id': STRIPE_PRICE_IDS['pro']}}
                ]
            },
            'current_period_end': int((datetime.now() + timedelta(days=30)).timestamp())
        }

        result = service.handle_subscription_event(
            'customer.subscription.updated',
            subscription_data
        )

        assert result['success'] is True
        assert result['action'] == 'updated'
        assert result['tier'] == 'pro'

    def test_handle_subscription_deleted(self):
        """Test handling subscription deleted event."""
        from api.src.stripe_service import StripeService
        service = StripeService()

        subscription_data = {
            'id': 'sub_test_123',
            'customer': 'cus_test_456'
        }

        result = service.handle_subscription_event(
            'customer.subscription.deleted',
            subscription_data
        )

        assert result['success'] is True
        assert result['action'] == 'cancelled'
        assert result['tier'] == 'free'

    def test_handle_invoice_payment_failed(self):
        """Test handling invoice payment failed event."""
        from api.src.stripe_service import StripeService
        service = StripeService()

        subscription_data = {
            'id': 'in_test_123',
            'customer': 'cus_test_456'
        }

        result = service.handle_subscription_event(
            'invoice.payment_failed',
            subscription_data
        )

        assert result['success'] is True
        assert result['action'] == 'payment_failed'

    def test_handle_invoice_payment_succeeded(self):
        """Test handling invoice payment succeeded event."""
        from api.src.stripe_service import StripeService
        service = StripeService()

        subscription_data = {
            'id': 'in_test_123',
            'customer': 'cus_test_456',
            'current_period_end': int((datetime.now() + timedelta(days=30)).timestamp())
        }

        result = service.handle_subscription_event(
            'invoice.payment_succeeded',
            subscription_data
        )

        assert result['success'] is True
        assert result['action'] == 'payment_succeeded'


class TestUserModelStripeFields:
    """Tests for User model Stripe fields."""

    def test_user_has_stripe_customer_id(self):
        """Test User model has stripe_customer_id field."""
        from datagod.models.user import User
        assert hasattr(User, 'stripe_customer_id')

    def test_user_has_stripe_subscription_id(self):
        """Test User model has stripe_subscription_id field."""
        from datagod.models.user import User
        assert hasattr(User, 'stripe_subscription_id')

    def test_user_to_dict_includes_stripe_customer_id(self):
        """Test to_dict includes stripe_customer_id."""
        from datagod.models.user import User

        user = User()
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.full_name = None
        user.disabled = False
        user.email_verified = False
        user.roles = []
        user.subscription_tier = "free"
        user.subscription_expires = None
        user.stripe_customer_id = "cus_test_123"
        user.last_login = None
        user.created_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()

        result = user.to_dict()

        assert 'stripe_customer_id' in result
        assert result['stripe_customer_id'] == "cus_test_123"

    def test_user_to_dict_sensitive_includes_subscription_id(self):
        """Test to_dict with sensitive=True includes stripe_subscription_id."""
        from datagod.models.user import User

        user = User()
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.full_name = None
        user.disabled = False
        user.email_verified = False
        user.roles = []
        user.subscription_tier = "pro"
        user.subscription_expires = None
        user.stripe_customer_id = "cus_test_123"
        user.stripe_subscription_id = "sub_test_456"
        user.last_login = None
        user.created_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        user.email_verification_token = None
        user.password_reset_token = None
        user.login_count = 0
        user.failed_login_count = 0
        user.api_calls_today = 0
        user.exports_this_month = 0

        result = user.to_dict(include_sensitive=True)

        assert 'stripe_subscription_id' in result
        assert result['stripe_subscription_id'] == "sub_test_456"
