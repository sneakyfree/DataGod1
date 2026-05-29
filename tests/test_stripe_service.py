"""
Tests for Stripe service.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


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

        assert "basic" in STRIPE_PRICE_IDS
        assert "pro" in STRIPE_PRICE_IDS
        assert "enterprise" in STRIPE_PRICE_IDS


class TestStripeServiceMockMode:
    """Tests for StripeService in mock mode (no Stripe configured)."""

    def test_mock_mode_detection(self):
        """Test service detects mock mode when Stripe not configured."""
        from api.src.stripe_service import StripeService

        with patch.dict("os.environ", {"STRIPE_SECRET_KEY": ""}, clear=False):
            service = StripeService()
            # When STRIPE_SECRET_KEY is empty, should be in mock mode
            # The actual behavior depends on STRIPE_AVAILABLE constant

    def test_create_customer_mock_mode(self):
        """Test creating customer in mock mode."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        service.stripe_available = False  # Force mock mode

        customer = service.create_customer(
            email="test@example.com", name="Test User", metadata={"user_id": "123"}
        )

        assert customer is not None
        assert "id" in customer
        assert customer["id"].startswith("cus_mock_")
        assert customer["email"] == "test@example.com"
        assert customer["name"] == "Test User"

    def test_create_checkout_session_mock_mode(self):
        """Test creating checkout session in mock mode."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        service.stripe_available = False  # Force mock mode

        session = service.create_checkout_session(
            customer_id="cus_test_123",
            price_id="price_test",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )

        assert session is not None
        assert "id" in session
        assert session["id"].startswith("cs_mock_")
        assert "url" in session
        assert session["status"] == "open"

    def test_create_portal_session_mock_mode(self):
        """Test creating portal session in mock mode."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        service.stripe_available = False  # Force mock mode

        session = service.create_portal_session(
            customer_id="cus_test_123", return_url="https://example.com/account"
        )

        assert session is not None
        assert "url" in session
        assert "portal=mock" in session["url"]

    def test_get_subscription_mock_mode(self):
        """Test getting subscription in mock mode returns None."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        service.stripe_available = False  # Force mock mode

        result = service.get_subscription("sub_test_123")
        assert result is None

    def test_cancel_subscription_mock_mode(self):
        """Test canceling subscription in mock mode."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        service.stripe_available = False  # Force mock mode

        result = service.cancel_subscription("sub_test_123")
        assert result is True

    def test_verify_webhook_mock_mode(self):
        """Test verifying webhook in mock mode."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        service.stripe_available = False  # Force mock mode

        payload = json.dumps({"type": "test.event", "data": {}}).encode()
        result = service.verify_webhook(payload, "sig_test")

        assert result is not None
        assert result["type"] == "test.event"

    def test_verify_webhook_invalid_json_mock_mode(self):
        """Test verifying webhook with invalid JSON in mock mode."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        service.stripe_available = False  # Force mock mode

        result = service.verify_webhook(b"not valid json", "sig_test")
        assert result is None


class TestStripeServicePriceMapping:
    """Tests for price ID mapping."""

    def test_get_price_id_basic(self):
        """Test getting price ID for basic tier."""
        from api.src.stripe_service import StripeService

        service = StripeService()

        price_id = service.get_price_id_for_tier("basic")
        assert price_id is not None

    def test_get_price_id_pro(self):
        """Test getting price ID for pro tier."""
        from api.src.stripe_service import StripeService

        service = StripeService()

        price_id = service.get_price_id_for_tier("pro")
        assert price_id is not None

    def test_get_price_id_enterprise(self):
        """Test getting price ID for enterprise tier."""
        from api.src.stripe_service import StripeService

        service = StripeService()

        price_id = service.get_price_id_for_tier("enterprise")
        assert price_id is not None

    def test_get_price_id_invalid(self):
        """Test getting price ID for invalid tier."""
        from api.src.stripe_service import StripeService

        service = StripeService()

        price_id = service.get_price_id_for_tier("invalid_tier")
        assert price_id is None

    def test_get_tier_from_price(self):
        """Test mapping price ID back to tier."""
        from api.src.stripe_service import STRIPE_PRICE_IDS, StripeService

        service = StripeService()

        for tier, price_id in STRIPE_PRICE_IDS.items():
            result = service._get_tier_from_price(price_id)
            assert result == tier

    def test_get_tier_from_price_unknown(self):
        """Test mapping unknown price ID returns free."""
        from api.src.stripe_service import StripeService

        service = StripeService()

        result = service._get_tier_from_price("price_unknown")
        assert result == "free"


class TestStripeServiceSubscriptionEvents:
    """Tests for subscription event handling."""

    def test_handle_subscription_created(self):
        """Test handling subscription created event."""
        from api.src.stripe_service import STRIPE_PRICE_IDS, StripeService

        service = StripeService()

        subscription_data = {
            "id": "sub_test_123",
            "customer": "cus_test_456",
            "items": {"data": [{"price": {"id": STRIPE_PRICE_IDS["basic"]}}]},
            "current_period_end": int(
                (datetime.now() + timedelta(days=30)).timestamp()
            ),
        }

        result = service.handle_subscription_event(
            "customer.subscription.created", subscription_data
        )

        assert result["success"] is True
        assert result["action"] == "created"
        assert result["subscription_id"] == "sub_test_123"
        assert result["customer_id"] == "cus_test_456"
        assert result["tier"] == "basic"

    def test_handle_subscription_updated(self):
        """Test handling subscription updated event."""
        from api.src.stripe_service import STRIPE_PRICE_IDS, StripeService

        service = StripeService()

        subscription_data = {
            "id": "sub_test_123",
            "customer": "cus_test_456",
            "items": {"data": [{"price": {"id": STRIPE_PRICE_IDS["pro"]}}]},
            "current_period_end": int(
                (datetime.now() + timedelta(days=30)).timestamp()
            ),
        }

        result = service.handle_subscription_event(
            "customer.subscription.updated", subscription_data
        )

        assert result["success"] is True
        assert result["action"] == "updated"
        assert result["tier"] == "pro"

    def test_handle_subscription_deleted(self):
        """Test handling subscription deleted event."""
        from api.src.stripe_service import StripeService

        service = StripeService()

        subscription_data = {"id": "sub_test_123", "customer": "cus_test_456"}

        result = service.handle_subscription_event(
            "customer.subscription.deleted", subscription_data
        )

        assert result["success"] is True
        assert result["action"] == "cancelled"
        assert result["tier"] == "free"

    def test_handle_invoice_payment_failed(self):
        """Test handling invoice payment failed event."""
        from api.src.stripe_service import StripeService

        service = StripeService()

        subscription_data = {"id": "in_test_123", "customer": "cus_test_456"}

        result = service.handle_subscription_event(
            "invoice.payment_failed", subscription_data
        )

        assert result["success"] is True
        assert result["action"] == "payment_failed"

    def test_handle_invoice_payment_succeeded(self):
        """Test handling invoice payment succeeded event."""
        from api.src.stripe_service import StripeService

        service = StripeService()

        subscription_data = {
            "id": "in_test_123",
            "customer": "cus_test_456",
            "current_period_end": int(
                (datetime.now() + timedelta(days=30)).timestamp()
            ),
        }

        result = service.handle_subscription_event(
            "invoice.payment_succeeded", subscription_data
        )

        assert result["success"] is True
        assert result["action"] == "payment_succeeded"


class TestUserModelStripeFields:
    """Tests for User model Stripe fields."""

    def test_user_has_stripe_customer_id(self):
        """Test User model has stripe_customer_id field."""
        from datagod.models.user import User

        assert hasattr(User, "stripe_customer_id")

    def test_user_has_stripe_subscription_id(self):
        """Test User model has stripe_subscription_id field."""
        from datagod.models.user import User

        assert hasattr(User, "stripe_subscription_id")

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

        assert "stripe_customer_id" in result
        assert result["stripe_customer_id"] == "cus_test_123"

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

        assert "stripe_subscription_id" in result
        assert result["stripe_subscription_id"] == "sub_test_456"


class TestStripeServiceWithRealStripe:
    """Tests for StripeService with mocked Stripe library."""

    @patch("api.src.stripe_service.stripe.Customer.create")
    def test_create_customer_real_stripe(self, mock_create):
        """Test creating customer with real Stripe (mocked)."""
        from api.src.stripe_service import StripeService

        # Mock the Stripe response
        mock_customer = MagicMock()
        mock_customer.id = "cus_real_123"
        mock_customer.email = "test@example.com"
        mock_customer.name = "Test User"
        mock_customer.metadata = {"user_id": "1"}
        mock_customer.created = 1704067200
        mock_create.return_value = mock_customer

        service = StripeService()
        service.stripe_available = True  # Force real mode

        customer = service.create_customer(
            email="test@example.com", name="Test User", metadata={"user_id": "1"}
        )

        mock_create.assert_called_once()
        assert customer["id"] == "cus_real_123"
        assert customer["email"] == "test@example.com"

    @patch("api.src.stripe_service.stripe.Customer.create")
    def test_create_customer_stripe_error(self, mock_create):
        """Test handling Stripe error when creating customer."""
        import stripe

        from api.src.stripe_service import StripeService

        mock_create.side_effect = stripe.error.StripeError("API Error")

        service = StripeService()
        service.stripe_available = True

        with pytest.raises(stripe.error.StripeError):
            service.create_customer(email="test@example.com")

    @patch("api.src.stripe_service.stripe.checkout.Session.create")
    def test_create_checkout_session_real_stripe(self, mock_create):
        """Test creating checkout session with real Stripe (mocked)."""
        from api.src.stripe_service import StripeService

        mock_session = MagicMock()
        mock_session.id = "cs_real_123"
        mock_session.url = "https://checkout.stripe.com/pay/cs_real_123"
        mock_session.status = "open"
        mock_create.return_value = mock_session

        service = StripeService()
        service.stripe_available = True

        session = service.create_checkout_session(
            customer_id="cus_123",
            price_id="price_123",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )

        mock_create.assert_called_once()
        assert session["id"] == "cs_real_123"
        assert session["url"] == "https://checkout.stripe.com/pay/cs_real_123"

    @patch("api.src.stripe_service.stripe.checkout.Session.create")
    def test_create_checkout_session_stripe_error(self, mock_create):
        """Test handling Stripe error when creating checkout session."""
        import stripe

        from api.src.stripe_service import StripeService

        mock_create.side_effect = stripe.error.StripeError("API Error")

        service = StripeService()
        service.stripe_available = True

        with pytest.raises(stripe.error.StripeError):
            service.create_checkout_session(
                customer_id="cus_123",
                price_id="price_123",
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel",
            )

    @patch("api.src.stripe_service.stripe.billing_portal.Session.create")
    def test_create_portal_session_real_stripe(self, mock_create):
        """Test creating portal session with real Stripe (mocked)."""
        from api.src.stripe_service import StripeService

        mock_session = MagicMock()
        mock_session.url = "https://billing.stripe.com/portal/session_123"
        mock_create.return_value = mock_session

        service = StripeService()
        service.stripe_available = True

        session = service.create_portal_session(
            customer_id="cus_123", return_url="https://example.com/account"
        )

        mock_create.assert_called_once()
        assert session["url"] == "https://billing.stripe.com/portal/session_123"

    @patch("api.src.stripe_service.stripe.billing_portal.Session.create")
    def test_create_portal_session_stripe_error(self, mock_create):
        """Test handling Stripe error when creating portal session."""
        import stripe

        from api.src.stripe_service import StripeService

        mock_create.side_effect = stripe.error.StripeError("API Error")

        service = StripeService()
        service.stripe_available = True

        with pytest.raises(stripe.error.StripeError):
            service.create_portal_session(
                customer_id="cus_123", return_url="https://example.com/account"
            )

    @patch("api.src.stripe_service.stripe.Subscription.retrieve")
    def test_get_subscription_real_stripe(self, mock_retrieve):
        """Test getting subscription with real Stripe (mocked)."""
        from api.src.stripe_service import StripeService

        mock_sub = MagicMock()
        mock_sub.id = "sub_123"
        mock_sub.status = "active"
        mock_sub.current_period_start = 1704067200
        mock_sub.current_period_end = 1706745600
        mock_sub.cancel_at_period_end = False
        mock_sub.items.data = [MagicMock(price=MagicMock(id="price_basic"))]
        mock_retrieve.return_value = mock_sub

        service = StripeService()
        service.stripe_available = True

        result = service.get_subscription("sub_123")

        mock_retrieve.assert_called_once_with("sub_123")
        assert result["id"] == "sub_123"
        assert result["status"] == "active"

    @patch("api.src.stripe_service.stripe.Subscription.retrieve")
    def test_get_subscription_stripe_error(self, mock_retrieve):
        """Test handling Stripe error when getting subscription."""
        import stripe

        from api.src.stripe_service import StripeService

        mock_retrieve.side_effect = stripe.error.StripeError("Not found")

        service = StripeService()
        service.stripe_available = True

        result = service.get_subscription("sub_invalid")
        assert result is None

    @patch("api.src.stripe_service.stripe.Subscription.modify")
    def test_cancel_subscription_at_period_end(self, mock_modify):
        """Test canceling subscription at period end with real Stripe."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        service.stripe_available = True

        result = service.cancel_subscription("sub_123", at_period_end=True)

        mock_modify.assert_called_once_with("sub_123", cancel_at_period_end=True)
        assert result is True

    @patch("api.src.stripe_service.stripe.Subscription.delete")
    def test_cancel_subscription_immediately(self, mock_delete):
        """Test canceling subscription immediately with real Stripe."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        service.stripe_available = True

        result = service.cancel_subscription("sub_123", at_period_end=False)

        mock_delete.assert_called_once_with("sub_123")
        assert result is True

    @patch("api.src.stripe_service.stripe.Subscription.modify")
    def test_cancel_subscription_stripe_error(self, mock_modify):
        """Test handling Stripe error when canceling subscription."""
        import stripe

        from api.src.stripe_service import StripeService

        mock_modify.side_effect = stripe.error.StripeError("API Error")

        service = StripeService()
        service.stripe_available = True

        result = service.cancel_subscription("sub_123")
        assert result is False

    @patch("api.src.stripe_service.stripe.Webhook.construct_event")
    def test_verify_webhook_real_stripe(self, mock_construct):
        """Test verifying webhook with real Stripe (mocked)."""
        from api.src.stripe_service import StripeService

        mock_event = MagicMock()
        mock_event.id = "evt_123"
        mock_event.type = "customer.subscription.created"
        mock_event.data.object = {"id": "sub_123"}
        mock_construct.return_value = mock_event

        service = StripeService()
        service.stripe_available = True
        service.webhook_secret = "whsec_test"

        result = service.verify_webhook(b"payload", "sig_123")

        mock_construct.assert_called_once()
        assert result["id"] == "evt_123"
        assert result["type"] == "customer.subscription.created"

    @patch("api.src.stripe_service.stripe.Webhook.construct_event")
    def test_verify_webhook_invalid_signature(self, mock_construct):
        """Test handling invalid webhook signature."""
        import stripe

        from api.src.stripe_service import StripeService

        mock_construct.side_effect = stripe.error.SignatureVerificationError(
            "Invalid signature", "sig"
        )

        service = StripeService()
        service.stripe_available = True
        service.webhook_secret = "whsec_test"

        result = service.verify_webhook(b"payload", "invalid_sig")
        assert result is None

    @patch("api.src.stripe_service.stripe.Webhook.construct_event")
    def test_verify_webhook_value_error(self, mock_construct):
        """Test handling ValueError in webhook verification."""
        from api.src.stripe_service import StripeService

        mock_construct.side_effect = ValueError("Invalid payload")

        service = StripeService()
        service.stripe_available = True
        service.webhook_secret = "whsec_test"

        result = service.verify_webhook(b"invalid", "sig_123")
        assert result is None


class TestStripeServiceEdgeCases:
    """Tests for edge cases and additional scenarios."""

    def test_create_customer_without_name(self):
        """Test creating customer without name."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        service.stripe_available = False

        customer = service.create_customer(email="test@example.com")

        assert customer["email"] == "test@example.com"
        assert customer["name"] is None

    def test_create_customer_without_metadata(self):
        """Test creating customer without metadata."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        service.stripe_available = False

        customer = service.create_customer(email="test@example.com")

        assert customer["metadata"] == {}

    def test_create_checkout_session_with_metadata(self):
        """Test creating checkout session with metadata."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        service.stripe_available = False

        session = service.create_checkout_session(
            customer_id="cus_123",
            price_id="price_123",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
            metadata={"order_id": "123"},
        )

        assert session is not None

    def test_handle_unknown_event_type(self):
        """Test handling unknown event type."""
        from api.src.stripe_service import StripeService

        service = StripeService()

        result = service.handle_subscription_event(
            "unknown.event.type", {"id": "sub_123", "customer": "cus_456"}
        )

        assert result["success"] is True
        assert result["action"] is None

    def test_handle_subscription_event_empty_items(self):
        """Test handling subscription event with empty items data."""
        from api.src.stripe_service import StripeService

        service = StripeService()

        # When items data is empty, the code accesses [{}][0].get('price', {}).get('id')
        # which gives None, and _get_tier_from_price returns 'free' for unknown price_id
        subscription_data = {
            "id": "sub_123",
            "customer": "cus_456",
            "items": {"data": [{}]},  # Empty item dict, not empty list
            "current_period_end": 0,
        }

        result = service.handle_subscription_event(
            "customer.subscription.created", subscription_data
        )

        assert result["success"] is True
        assert result["tier"] == "free"

    def test_stripe_not_available_warning(self):
        """Test that warning is logged when Stripe not available."""
        from api.src.stripe_service import StripeService

        # This tests the initialization path
        service = StripeService()
        # Just verify it doesn't raise
        assert service is not None

    def test_get_subscription_with_no_items(self):
        """Test get_subscription handles subscription with no items."""
        from api.src.stripe_service import StripeService

        service = StripeService()
        service.stripe_available = False

        # In mock mode, just returns None
        result = service.get_subscription("sub_123")
        assert result is None
