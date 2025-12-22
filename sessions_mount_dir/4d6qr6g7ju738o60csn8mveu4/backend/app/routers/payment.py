from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
import stripe
import logging
from datetime import datetime, timedelta

from .. import models, schemas
from ..database import get_db
from ..dependencies import get_current_user

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Stripe (ensure to set your secret key in environment variables)
stripe.api_key = "sk_test_your_stripe_secret_key"  # Replace with your actual secret key

router = APIRouter(prefix="/payment", tags=["payment"])

@router.post("/create-payment-intent", response_model=Dict[str, Any])
def create_payment_intent(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Create a Stripe Payment Intent for a given plan.
    """
    # Fetch the plan
    plan = db.query(models.Plan).filter(models.Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )

    # Ensure the user has a Stripe customer ID
    if not current_user.stripe_customer_id:
        try:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.full_name or current_user.username,
                metadata={"user_id": current_user.id}
            )
            current_user.stripe_customer_id = customer.id
            db.commit()
        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create Stripe customer"
            )

    # Create Payment Intent
    try:
        intent = stripe.PaymentIntent.create(
            amount=plan.price,
            currency=plan.currency.lower(),
            customer=current_user.stripe_customer_id,
            metadata={
                "plan_id": plan.id,
                "user_id": current_user.id
            },
            automatic_payment_methods={"enabled": True}
        )
    except stripe.error.StripeError as e:
        logger.error(f"Payment Intent creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create payment intent"
        )

    # Create an order in pending state
    order = models.Order(
        user_id=current_user.id,
        plan_id=plan.id,
        amount=plan.price,
        currency=plan.currency,
        status=models.OrderStatus.PENDING,
        stripe_payment_intent_id=intent.id
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    return {
        "client_secret": intent.client_secret,
        "order_id": order.id
    }

@router.post("/confirm-payment", response_model=schemas.Order)
def confirm_payment(
    payment_intent_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Confirm a payment and update the order status.
    """
    # Fetch the order
    order = db.query(models.Order).filter(
        models.Order.stripe_payment_intent_id == payment_intent_id,
        models.Order.user_id == current_user.id
    ).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Retrieve the Payment Intent from Stripe
    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    except stripe.error.StripeError as e:
        logger.error(f"Payment Intent retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to retrieve payment intent"
        )

    # Update order status based on Payment Intent status
    if intent.status == "succeeded":
        order.status = models.OrderStatus.COMPLETED
        # Update user membership
        plan = order.plan
        if plan.type == models.PlanType.LIFETIME:
            current_user.membership_expires_at = None
            current_user.is_premium = True
        else:
            extension = timedelta(days=plan.duration_days)
            if current_user.membership_expires_at and current_user.membership_expires_at > datetime.utcnow():
                current_user.membership_expires_at += extension
            else:
                current_user.membership_expires_at = datetime.utcnow() + extension
            current_user.is_premium = True
        db.commit()
    elif intent.status == "canceled":
        order.status = models.OrderStatus.FAILED
        db.commit()
    else:
        # For other statuses, keep the order as pending
        pass

    db.refresh(order)
    return order

@router.post("/webhook", response_model=Dict[str, str])
def stripe_webhook(
    payload: bytes,
    stripe_signature: str,
    db: Session = Depends(get_db)
):
    """
    Handle Stripe webhooks for asynchronous events.
    """
    endpoint_secret = "whsec_your_webhook_secret"  # Replace with your actual webhook secret
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        logger.error(f"Invalid payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload"
        )
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error(f"Invalid signature: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )

    # Handle the event
    if event.type == "payment_intent.succeeded":
        payment_intent = event.data.object  # Contains a Stripe PaymentIntent
        handle_payment_succeeded(payment_intent, db)
    elif event.type == "payment_intent.payment_failed":
        payment_intent = event.data.object
        handle_payment_failed(payment_intent, db)
    else:
        logger.warning(f"Unhandled event type: {event.type}")

    return {"status": "success"}

def handle_payment_succeeded(payment_intent: stripe.PaymentIntent, db: Session):
    """
    Handle a successful payment event.
    """
    order = db.query(models.Order).filter(
        models.Order.stripe_payment_intent_id == payment_intent.id
    ).first()
    if not order:
        logger.error(f"Order not found for PaymentIntent: {payment_intent.id}")
        return

    if order.status != models.OrderStatus.COMPLETED:
        order.status = models.OrderStatus.COMPLETED
        # Update user membership
        plan = order.plan
        user = order.user
        if plan.type == models.PlanType.LIFETIME:
            user.membership_expires_at = None
            user.is_premium = True
        else:
            extension = timedelta(days=plan.duration_days)
            if user.membership_expires_at and user.membership_expires_at > datetime.utcnow():
                user.membership_expires_at += extension
            else:
                user.membership_expires_at = datetime.utcnow() + extension
            user.is_premium = True
        db.commit()
        logger.info(f"Payment succeeded for Order: {order.id}")

def handle_payment_failed(payment_intent: stripe.PaymentIntent, db: Session):
    """
    Handle a failed payment event.
    """
    order = db.query(models.Order).filter(
        models.Order.stripe_payment_intent_id == payment_intent.id
    ).first()
    if not order:
        logger.error(f"Order not found for PaymentIntent: {payment_intent.id}")
        return

    if order.status != models.OrderStatus.FAILED:
        order.status = models.OrderStatus.FAILED
        db.commit()
        logger.info(f"Payment failed for Order: {order.id}")
