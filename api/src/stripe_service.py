"""
Stripe integration service for DataGod payment processing.

This service handles:
- Customer management
- Checkout session creation
- Subscription management
- Webhook handling
- Billing portal access
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Stripe price IDs for each tier (set in environment variables)
STRIPE_PRICE_IDS = {
    'basic': os.getenv('STRIPE_PRICE_ID_BASIC', 'price_basic_placeholder'),
    'pro': os.getenv('STRIPE_PRICE_ID_PRO', 'price_pro_placeholder'),
    'enterprise': os.getenv('STRIPE_PRICE_ID_ENTERPRISE', 'price_enterprise_placeholder'),
}

# Try to import Stripe - optional dependency
try:
    import stripe
    STRIPE_AVAILABLE = True
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY', '')
except ImportError:
    STRIPE_AVAILABLE = False
    logger.warning("Stripe library not installed. Payment features will use mock mode.")


class StripeService:
    """
    Handles Stripe payment operations.

    When Stripe is not configured, operates in mock mode for development.
    """

    def __init__(self):
        self.stripe_available = STRIPE_AVAILABLE and bool(os.getenv('STRIPE_SECRET_KEY'))
        self.webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET', '')

        if not self.stripe_available:
            logger.info("Stripe not configured - running in mock mode")

    def create_customer(self, email: str, name: Optional[str] = None,
                       metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create a Stripe customer for a user.

        Args:
            email: Customer email
            name: Customer name
            metadata: Additional metadata (e.g., user_id)

        Returns:
            Customer object with id and other details
        """
        if not self.stripe_available:
            # Mock mode - return fake customer
            return {
                'id': f'cus_mock_{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'email': email,
                'name': name,
                'metadata': metadata or {},
                'created': int(datetime.now().timestamp()),
            }

        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {},
            )
            return {
                'id': customer.id,
                'email': customer.email,
                'name': customer.name,
                'metadata': customer.metadata,
                'created': customer.created,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating customer: {e}")
            raise

    def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout session for subscription purchase.

        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID for the subscription
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancel
            metadata: Additional metadata

        Returns:
            Checkout session with id and url
        """
        if not self.stripe_available:
            # Mock mode - return fake session
            session_id = f'cs_mock_{datetime.now().strftime("%Y%m%d%H%M%S")}'
            return {
                'id': session_id,
                'url': f'{success_url}?session_id={session_id}&mock=true',
                'status': 'open',
            }

        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                mode='subscription',
                line_items=[{'price': price_id, 'quantity': 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata or {},
            )
            return {
                'id': session.id,
                'url': session.url,
                'status': session.status,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            raise

    def create_portal_session(
        self,
        customer_id: str,
        return_url: str
    ) -> Dict[str, Any]:
        """
        Create a Stripe Billing Portal session for subscription management.

        Args:
            customer_id: Stripe customer ID
            return_url: URL to return to after portal session

        Returns:
            Portal session with url
        """
        if not self.stripe_available:
            # Mock mode
            return {
                'url': f'{return_url}?portal=mock',
            }

        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return {'url': session.url}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating portal session: {e}")
            raise

    def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """
        Get subscription details.

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            Subscription details or None if not found
        """
        if not self.stripe_available:
            return None

        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return {
                'id': subscription.id,
                'status': subscription.status,
                'current_period_start': subscription.current_period_start,
                'current_period_end': subscription.current_period_end,
                'cancel_at_period_end': subscription.cancel_at_period_end,
                'plan': subscription.items.data[0].price.id if subscription.items.data else None,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error getting subscription: {e}")
            return None

    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> bool:
        """
        Cancel a subscription.

        Args:
            subscription_id: Stripe subscription ID
            at_period_end: If True, cancel at end of billing period

        Returns:
            True if successful
        """
        if not self.stripe_available:
            return True

        try:
            if at_period_end:
                stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                stripe.Subscription.delete(subscription_id)
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error canceling subscription: {e}")
            return False

    def verify_webhook(self, payload: bytes, signature: str) -> Optional[Dict[str, Any]]:
        """
        Verify and parse a Stripe webhook event.

        Args:
            payload: Raw request body
            signature: Stripe-Signature header

        Returns:
            Parsed event or None if invalid
        """
        if not self.stripe_available:
            # Mock mode - try to parse JSON directly
            import json
            try:
                return json.loads(payload)
            except:
                return None

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            return {
                'id': event.id,
                'type': event.type,
                'data': event.data.object,
            }
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            logger.error(f"Invalid webhook: {e}")
            return None

    def get_price_id_for_tier(self, tier: str) -> Optional[str]:
        """
        Get the Stripe price ID for a subscription tier.

        Args:
            tier: Subscription tier (basic, pro, enterprise)

        Returns:
            Price ID or None if tier not found
        """
        return STRIPE_PRICE_IDS.get(tier)

    def handle_subscription_event(
        self,
        event_type: str,
        subscription_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a subscription-related webhook event.

        Args:
            event_type: Stripe event type
            subscription_data: Subscription object from webhook

        Returns:
            Dict with processing result and user update info
        """
        result = {
            'success': True,
            'action': None,
            'subscription_id': subscription_data.get('id'),
            'customer_id': subscription_data.get('customer'),
            'tier': None,
            'expires_at': None,
        }

        if event_type == 'customer.subscription.created':
            result['action'] = 'created'
            result['tier'] = self._get_tier_from_price(
                subscription_data.get('items', {}).get('data', [{}])[0].get('price', {}).get('id')
            )
            result['expires_at'] = datetime.fromtimestamp(
                subscription_data.get('current_period_end', 0)
            )

        elif event_type == 'customer.subscription.updated':
            result['action'] = 'updated'
            result['tier'] = self._get_tier_from_price(
                subscription_data.get('items', {}).get('data', [{}])[0].get('price', {}).get('id')
            )
            result['expires_at'] = datetime.fromtimestamp(
                subscription_data.get('current_period_end', 0)
            )

        elif event_type == 'customer.subscription.deleted':
            result['action'] = 'cancelled'
            result['tier'] = 'free'

        elif event_type == 'invoice.payment_failed':
            result['action'] = 'payment_failed'

        elif event_type == 'invoice.payment_succeeded':
            result['action'] = 'payment_succeeded'
            result['expires_at'] = datetime.fromtimestamp(
                subscription_data.get('current_period_end', 0)
            )

        return result

    def _get_tier_from_price(self, price_id: str) -> str:
        """Map a Stripe price ID to subscription tier."""
        for tier, pid in STRIPE_PRICE_IDS.items():
            if pid == price_id:
                return tier
        return 'free'


# Global service instance
stripe_service = StripeService()
