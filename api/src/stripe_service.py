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
from typing import Dict, Any, Optional, List
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
    
    def _generate_idempotency_key(self, operation: str, *args) -> str:
        """Generate an idempotency key for deduplicating requests."""
        import hashlib
        key_data = f"{operation}:{':'.join(str(a) for a in args)}:{datetime.now().strftime('%Y%m%d%H')}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]
    
    # ==================== PRODUCTION ENHANCEMENTS ====================
    
    def upgrade_subscription(
        self,
        subscription_id: str,
        new_price_id: str,
        prorate: bool = True
    ) -> Dict[str, Any]:
        """
        Upgrade or downgrade a subscription with proration.
        
        Args:
            subscription_id: Current subscription ID
            new_price_id: New price ID to switch to
            prorate: Whether to prorate charges
            
        Returns:
            Updated subscription details
        """
        if not self.stripe_available:
            return {
                'id': subscription_id,
                'status': 'active',
                'price_id': new_price_id,
                'proration_applied': prorate,
            }
        
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            # Get the subscription item ID
            item_id = subscription.items.data[0].id if subscription.items.data else None
            if not item_id:
                raise ValueError("No subscription items found")
            
            # Update with proration
            updated = stripe.Subscription.modify(
                subscription_id,
                items=[{
                    'id': item_id,
                    'price': new_price_id,
                }],
                proration_behavior='create_prorations' if prorate else 'none',
                idempotency_key=self._generate_idempotency_key('upgrade', subscription_id, new_price_id),
            )
            
            logger.info(f"Subscription {subscription_id} upgraded to {new_price_id}")
            
            return {
                'id': updated.id,
                'status': updated.status,
                'price_id': new_price_id,
                'current_period_end': updated.current_period_end,
                'proration_applied': prorate,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error upgrading subscription: {e}")
            raise
    
    def preview_proration(
        self,
        subscription_id: str,
        new_price_id: str
    ) -> Dict[str, Any]:
        """
        Preview proration charges for a subscription change.
        
        Args:
            subscription_id: Current subscription ID
            new_price_id: New price ID to preview
            
        Returns:
            Proration preview with amounts
        """
        if not self.stripe_available:
            return {
                'amount': 0,
                'currency': 'usd',
                'preview_line_items': [],
            }
        
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            # Create upcoming invoice preview
            invoice = stripe.Invoice.upcoming(
                customer=subscription.customer,
                subscription=subscription_id,
                subscription_items=[{
                    'id': subscription.items.data[0].id,
                    'price': new_price_id,
                }],
                subscription_proration_behavior='create_prorations',
            )
            
            return {
                'amount_due': invoice.amount_due / 100,  # Convert from cents
                'currency': invoice.currency,
                'proration_date': datetime.utcnow().isoformat(),
                'line_items': [
                    {
                        'description': item.description,
                        'amount': item.amount / 100,
                        'proration': item.proration,
                    }
                    for item in invoice.lines.data
                ],
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error previewing proration: {e}")
            raise
    
    def get_invoices(
        self,
        customer_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get invoice history for a customer.
        
        Args:
            customer_id: Stripe customer ID
            limit: Maximum invoices to return
            
        Returns:
            List of invoice summaries
        """
        if not self.stripe_available:
            return []
        
        try:
            invoices = stripe.Invoice.list(
                customer=customer_id,
                limit=limit,
            )
            
            return [
                {
                    'id': inv.id,
                    'number': inv.number,
                    'status': inv.status,
                    'amount_due': inv.amount_due / 100,
                    'amount_paid': inv.amount_paid / 100,
                    'currency': inv.currency,
                    'created': datetime.fromtimestamp(inv.created).isoformat(),
                    'period_start': datetime.fromtimestamp(inv.period_start).isoformat() if inv.period_start else None,
                    'period_end': datetime.fromtimestamp(inv.period_end).isoformat() if inv.period_end else None,
                    'hosted_invoice_url': inv.hosted_invoice_url,
                    'pdf_url': inv.invoice_pdf,
                }
                for inv in invoices.data
            ]
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error listing invoices: {e}")
            return []
    
    def retry_failed_payment(self, invoice_id: str) -> Dict[str, Any]:
        """
        Retry a failed invoice payment.
        
        Args:
            invoice_id: Failed invoice ID
            
        Returns:
            Updated invoice status
        """
        if not self.stripe_available:
            return {'success': False, 'message': 'Stripe not configured'}
        
        try:
            invoice = stripe.Invoice.pay(
                invoice_id,
                idempotency_key=self._generate_idempotency_key('retry', invoice_id),
            )
            
            return {
                'success': invoice.status == 'paid',
                'invoice_id': invoice.id,
                'status': invoice.status,
                'amount_paid': invoice.amount_paid / 100,
            }
            
        except stripe.error.CardError as e:
            logger.warning(f"Card error retrying payment: {e}")
            return {
                'success': False,
                'error': 'card_error',
                'message': str(e.user_message),
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error retrying payment: {e}")
            raise
    
    def update_payment_method(
        self,
        customer_id: str,
        payment_method_id: str
    ) -> Dict[str, Any]:
        """
        Update the default payment method for a customer.
        
        Args:
            customer_id: Stripe customer ID
            payment_method_id: New payment method ID
            
        Returns:
            Updated customer info
        """
        if not self.stripe_available:
            return {'success': True, 'payment_method': payment_method_id}
        
        try:
            # Attach payment method to customer
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id,
            )
            
            # Set as default
            stripe.Customer.modify(
                customer_id,
                invoice_settings={'default_payment_method': payment_method_id},
            )
            
            return {
                'success': True,
                'customer_id': customer_id,
                'payment_method': payment_method_id,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error updating payment method: {e}")
            raise
    
    def get_payment_methods(self, customer_id: str) -> List[Dict[str, Any]]:
        """
        List payment methods for a customer.
        
        Args:
            customer_id: Stripe customer ID
            
        Returns:
            List of payment methods
        """
        if not self.stripe_available:
            return []
        
        try:
            methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type='card',
            )
            
            return [
                {
                    'id': pm.id,
                    'type': pm.type,
                    'brand': pm.card.brand if pm.card else None,
                    'last4': pm.card.last4 if pm.card else None,
                    'exp_month': pm.card.exp_month if pm.card else None,
                    'exp_year': pm.card.exp_year if pm.card else None,
                }
                for pm in methods.data
            ]
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error listing payment methods: {e}")
            return []
    
    def create_usage_record(
        self,
        subscription_item_id: str,
        quantity: int,
        action: str = 'increment'
    ) -> Dict[str, Any]:
        """
        Record usage for metered billing.
        
        Args:
            subscription_item_id: Subscription item ID
            quantity: Usage amount
            action: 'increment' or 'set'
            
        Returns:
            Usage record details
        """
        if not self.stripe_available:
            return {
                'id': f'mbur_mock_{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'quantity': quantity,
            }
        
        try:
            record = stripe.SubscriptionItem.create_usage_record(
                subscription_item_id,
                quantity=quantity,
                action=action,
                timestamp=int(datetime.utcnow().timestamp()),
                idempotency_key=self._generate_idempotency_key('usage', subscription_item_id, quantity),
            )
            
            return {
                'id': record.id,
                'quantity': record.quantity,
                'timestamp': record.timestamp,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating usage record: {e}")
            raise
    
    def get_usage_summary(self, subscription_item_id: str) -> Dict[str, Any]:
        """
        Get usage summary for current billing period.
        
        Args:
            subscription_item_id: Subscription item ID
            
        Returns:
            Usage summary
        """
        if not self.stripe_available:
            return {'total_usage': 0, 'period': 'current'}
        
        try:
            usage = stripe.SubscriptionItem.list_usage_record_summaries(
                subscription_item_id,
                limit=1,
            )
            
            if usage.data:
                summary = usage.data[0]
                return {
                    'total_usage': summary.total_usage,
                    'period_start': datetime.fromtimestamp(summary.period.start).isoformat(),
                    'period_end': datetime.fromtimestamp(summary.period.end).isoformat(),
                }
            
            return {'total_usage': 0, 'period': 'current'}
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error getting usage summary: {e}")
            return {'total_usage': 0, 'period': 'current'}
    
    def apply_coupon(
        self,
        customer_id: str,
        coupon_code: str
    ) -> Dict[str, Any]:
        """
        Apply a coupon/discount to a customer.
        
        Args:
            customer_id: Stripe customer ID
            coupon_code: Coupon code to apply
            
        Returns:
            Discount details
        """
        if not self.stripe_available:
            return {'success': True, 'coupon': coupon_code}
        
        try:
            # Validate coupon first
            coupon = stripe.Coupon.retrieve(coupon_code)
            
            # Apply to customer
            customer = stripe.Customer.modify(
                customer_id,
                coupon=coupon_code,
            )
            
            return {
                'success': True,
                'coupon': coupon_code,
                'percent_off': coupon.percent_off,
                'amount_off': coupon.amount_off / 100 if coupon.amount_off else None,
                'duration': coupon.duration,
            }
            
        except stripe.error.InvalidRequestError as e:
            if 'No such coupon' in str(e):
                return {'success': False, 'error': 'Invalid coupon code'}
            raise
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error applying coupon: {e}")
            raise
    
    def get_customer_billing_details(self, customer_id: str) -> Dict[str, Any]:
        """
        Get comprehensive billing details for a customer.
        
        Args:
            customer_id: Stripe customer ID
            
        Returns:
            Complete billing summary
        """
        if not self.stripe_available:
            return {
                'customer_id': customer_id,
                'subscription': None,
                'payment_methods': [],
                'invoices': [],
            }
        
        try:
            customer = stripe.Customer.retrieve(customer_id, expand=['subscriptions'])
            
            # Get active subscription
            subscription = None
            if customer.subscriptions.data:
                sub = customer.subscriptions.data[0]
                subscription = {
                    'id': sub.id,
                    'status': sub.status,
                    'tier': self._get_tier_from_price(
                        sub.items.data[0].price.id if sub.items.data else None
                    ),
                    'current_period_start': datetime.fromtimestamp(sub.current_period_start).isoformat(),
                    'current_period_end': datetime.fromtimestamp(sub.current_period_end).isoformat(),
                    'cancel_at_period_end': sub.cancel_at_period_end,
                }
            
            return {
                'customer_id': customer_id,
                'email': customer.email,
                'name': customer.name,
                'subscription': subscription,
                'payment_methods': self.get_payment_methods(customer_id),
                'recent_invoices': self.get_invoices(customer_id, limit=5),
                'balance': customer.balance / 100 if customer.balance else 0,
                'default_payment_method': customer.invoice_settings.default_payment_method if customer.invoice_settings else None,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error getting billing details: {e}")
            raise


# Global service instance
stripe_service = StripeService()
