import stripe
from typing import Dict, Any, Optional
from ..core.payment_gateway import PaymentGateway, PaymentStatus
import logging

logger = logging.getLogger(__name__)

class StripeGateway(PaymentGateway):
    """
    Stripe payment gateway implementation.
    """

    def validate_config(self) -> None:
        required_keys = ['secret_key', 'publishable_key', 'webhook_secret']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required config key: {key}")
        
        # Initialize Stripe with the secret key
        stripe.api_key = self.config['secret_key']

    def create_payment(self, amount: float, currency: str, description: str, 
                      metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            # Convert amount to cents (Stripe uses smallest currency unit)
            amount_cents = int(amount * 100)
            
            # Create a PaymentIntent
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                description=description,
                metadata=metadata or {}
            )
            
            return {
                "payment_id": intent.id,
                "client_secret": intent.client_secret,
                "status": self._map_stripe_status(intent.status).value.value
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment creation failed: {str(e)}")
            raise

    def capture_payment(self, payment_id: str) -> Dict[str, Any]:
        try:
            # Retrieve the PaymentIntent
            intent = stripe.PaymentIntent.retrieve(payment_id)
            
            # Confirm the payment (this captures it)
            if intent.status == 'requires_confirmation':
                intent = stripe.PaymentIntent.confirm(payment_id)
            
            return {
                "payment_id": intent.id,
                "status": self._map_stripe_status(intent.status)
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment capture failed: {str(e)}")
            raise

    def refund_payment(self, payment_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        try:
            refund_params = {
                'payment_intent': payment_id
            }
            
            if amount is not None:
                refund_params['amount'] = int(amount * 100)
            
            refund = stripe.Refund.create(**refund_params)
            
            return {
                "payment_id": payment_id,
                "refund_id": refund.id,
                "status": PaymentStatus.REFUNDED.value
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment refund failed: {str(e)}")
            raise

    def get_payment_status(self, payment_id: str) -> PaymentStatus:
        try:
            intent = stripe.PaymentIntent.retrieve(payment_id)
            return self._map_stripe_status(intent.status)
        except stripe.error.StripeError as e:
            logger.error(f"Stripe status check failed: {str(e)}")
            raise

    def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Verify the webhook signature
            sig_header = payload.get('stripe-signature')
            if not sig_header:
                raise ValueError("Missing stripe-signature header")
            
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.config['webhook_secret']
            )
            
            # Handle different event types
            if event.type == 'payment_intent.succeeded':
                payment_intent = event.data.object
                return {
                    "payment_id": payment_intent.id,
                    "status": PaymentStatus.SUCCESS.value,
                    "event_type": event.type
                }
            elif event.type == 'payment_intent.payment_failed':
                payment_intent = event.data.object
                return {
                    "payment_id": payment_intent.id,
                    "status": PaymentStatus.FAILED.value,
                    "event_type": event.type
                }
            elif event.type == 'payment_intent.canceled':
                payment_intent = event.data.object
                return {
                    "payment_id": payment_intent.id,
                    "status": PaymentStatus.CANCELLED.value,
                    "event_type": event.type
                }
            else:
                return {
                    "event_type": event.type,
                    "status": "unhandled"
                }
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Stripe webhook signature verification failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Stripe webhook handling failed: {str(e)}")
            raise

    def _map_stripe_status(self, stripe_status: str) -> PaymentStatus:
        """
        Map Stripe status to our PaymentStatus enum.
        """
        status_mapping = {
            'requires_payment_method': PaymentStatus.PENDING,
            'requires_confirmation': PaymentStatus.PENDING,
            'requires_action': PaymentStatus.PENDING,
            'processing': PaymentStatus.PENDING,
            'succeeded': PaymentStatus.SUCCESS,
            'canceled': PaymentStatus.CANCELLED,
            'requires_capture': PaymentStatus.PENDING
        }
        return status_mapping.get(stripe_status, PaymentStatus.FAILED)
