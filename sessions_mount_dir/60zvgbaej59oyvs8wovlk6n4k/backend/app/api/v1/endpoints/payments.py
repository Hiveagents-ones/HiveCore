from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from app import crud, schemas, models
from app.api.deps import get_db, get_current_active_user
from app.core.config import settings
from app.models import PaymentStatus
from app.models import Payment, Notification, NotificationType, NotificationStatus
import stripe
import logging
import time
from prometheus_client import Counter, Histogram, generate_latest
from fastapi import Response

router = APIRouter()

# Metrics
PAYMENT_REQUESTS = Counter('payment_requests_total', 'Total payment requests', ['endpoint', 'status'])
PAYMENT_DURATION = Histogram('payment_duration_seconds', 'Payment processing duration')

# Logger
logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

@router.post("/", response_model=schemas.Payment)
@PAYMENT_DURATION.time()
def initiate_payment(
    payment: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Initiate a new payment for membership renewal"""

    start_time = time.time()
    logger.info(f"Initiating payment for member {payment.member_id}, amount: {payment.amount}")
    # Verify member exists
    member = crud.get_member(db, payment.member_id)
    if not member:
        logger.error(f"Member {payment.member_id} not found")
        PAYMENT_REQUESTS.labels(endpoint='initiate', status='404').inc()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    # Create payment intent with Stripe
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(payment.amount * 100),  # Convert to cents
            currency='usd',
            metadata={
                'member_id': payment.member_id,
                'months': payment.months
            }
        )
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error for member {payment.member_id}: {str(e)}")
        PAYMENT_REQUESTS.labels(endpoint='initiate', status='400').inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment processing error: {str(e)}"
        )

    # Create payment record
    db_payment = crud.create_payment(
        db=db,
        payment=schemas.PaymentCreate(
            member_id=payment.member_id,
            amount=payment.amount,
            months=payment.months,
            stripe_payment_intent_id=intent.id,
            status=PaymentStatus.PENDING
        )
    )

    logger.info(f"Payment initiated successfully for member {payment.member_id}, intent ID: {intent.id}")
    PAYMENT_REQUESTS.labels(endpoint='initiate', status='200').inc()
    duration = time.time() - start_time
    logger.info(f"Payment initiation took {duration:.2f} seconds")

    return {
        **db_payment.__dict__,
        'client_secret': intent.client_secret
    }

@router.post("/confirm", response_model=schemas.Payment)
@PAYMENT_DURATION.time()
def confirm_payment(
    payment_intent_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Confirm payment after Stripe webhook"""

    start_time = time.time()
    logger.info(f"Confirming payment for intent {payment_intent_id}")
    # Retrieve payment intent from Stripe
    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    except stripe.error.StripeError as e:
        logger.error(f"Stripe retrieval error for intent {payment_intent_id}: {str(e)}")
        PAYMENT_REQUESTS.labels(endpoint='confirm', status='400').inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment retrieval error: {str(e)}"
        )

    # Get payment from database
    payment = crud.get_payment_by_intent(db, payment_intent_id)
    if not payment:
        logger.error(f"Payment not found for intent {payment_intent_id}")
        PAYMENT_REQUESTS.labels(endpoint='confirm', status='404').inc()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    # Update payment status based on Stripe status
    if intent.status == 'succeeded':
        payment_status = PaymentStatus.COMPLETED
        # Update member's remaining months
        member = crud.get_member(db, payment.member_id)
        if member:
            member.remaining_months += payment.months
            # Create renewal notification
            notification = Notification(
                member_id=payment.member_id,
                type=NotificationType.EMAIL,
                status=NotificationStatus.PENDING,
                message=f"Your membership has been renewed for {payment.months} months."
            )
            db.add(notification)
            db.commit()
    else:
        payment_status = PaymentStatus.FAILED

    # Update payment record
    updated_payment = crud.update_payment_status(
        db=db,
        payment_id=payment.id,
        status=payment_status
    )

    logger.info(f"Payment {payment_intent_id} confirmed with status {payment_status}")
    PAYMENT_REQUESTS.labels(endpoint='confirm', status='200').inc()
    duration = time.time() - start_time
    logger.info(f"Payment confirmation took {duration:.2f} seconds")

    return updated_payment

@router.get("/history", response_model=List[schemas.Payment])
@PAYMENT_DURATION.time()
def get_payment_history(
    member_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get payment history for a member"""

    start_time = time.time()
    logger.info(f"Fetching payment history for member {member_id}")
    # Verify member exists
    member = crud.get_member(db, member_id)
    if not member:
        logger.error(f"Member {member_id} not found when fetching payment history")
        PAYMENT_REQUESTS.labels(endpoint='history', status='404').inc()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    payments = crud.get_payments_by_member(
        db=db,
        member_id=member_id,
        skip=skip,
        limit=limit
    )

    logger.info(f"Retrieved {len(payments)} payment records for member {member_id}")
    PAYMENT_REQUESTS.labels(endpoint='history', status='200').inc()
    duration = time.time() - start_time
    logger.info(f"Payment history fetch took {duration:.2f} seconds")

    return payments

@router.get("/{payment_id}", response_model=schemas.Payment)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get payment details by ID"""
    payment = crud.get_payment(db, payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    return payment

@router.post("/webhook")
@PAYMENT_DURATION.time()
def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhooks"""

    start_time = time.time()
    logger.info("Processing Stripe webhook")
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {str(e)}")
        PAYMENT_REQUESTS.labels(endpoint='webhook', status='400').inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload"
        )
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {str(e)}")
        PAYMENT_REQUESTS.labels(endpoint='webhook', status='400').inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )

    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        # Update payment status
        payment = crud.get_payment_by_intent(db, payment_intent['id'])
        if payment:
            crud.update_payment_status(
                db=db,
                payment_id=payment.id,
                status=PaymentStatus.COMPLETED
            )
            # Update member's remaining months
            member = crud.get_member(db, payment.member_id)
            if member:
                member.remaining_months += payment.months
                # Create renewal notification
                notification = Notification(
                    member_id=payment.member_id,
                    type=NotificationType.EMAIL,
                    status=NotificationStatus.PENDING,
                    message=f"Your membership has been renewed for {payment.months} months."
                )
                db.add(notification)
                db.commit()
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        # Update payment status
        payment = crud.get_payment_by_intent(db, payment_intent['id'])
        if payment:
            crud.update_payment_status(
                db=db,
                payment_id=payment.id,
                status=PaymentStatus.FAILED
            )
            # Create failure notification
            notification = Notification(
                member_id=payment.member_id,
                type=NotificationType.EMAIL,
                status=NotificationStatus.PENDING,
                message="Your payment failed. Please try again or contact support."
            )
            db.add(notification)
            db.commit()

    logger.info(f"Webhook processed successfully for event type: {event['type']}")
    PAYMENT_REQUESTS.labels(endpoint='webhook', status='200').inc()
    duration = time.time() - start_time
    logger.info(f"Webhook processing took {duration:.2f} seconds")

    return {"status": "success"}


@router.get("/metrics")
def get_metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type="text/plain")

@router.post("/refund/{payment_id}")
@PAYMENT_DURATION.time()
def refund_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Process a refund for a payment"""
    
    start_time = time.time()
    logger.info(f"Processing refund for payment {payment_id}")
    
    # Get payment from database
    payment = crud.get_payment(db, payment_id)
    if not payment:
        logger.error(f"Payment {payment_id} not found")
        PAYMENT_REQUESTS.labels(endpoint='refund', status='404').inc()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    if payment.status != PaymentStatus.COMPLETED:
        logger.error(f"Cannot refund payment {payment_id} with status {payment.status}")
        PAYMENT_REQUESTS.labels(endpoint='refund', status='400').inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only completed payments can be refunded"
        )
    
    # Process refund with Stripe
    try:
        refund = stripe.Refund.create(
            payment_intent=payment.stripe_payment_intent_id
        )
    except stripe.error.StripeError as e:
        logger.error(f"Stripe refund error for payment {payment_id}: {str(e)}")
        PAYMENT_REQUESTS.labels(endpoint='refund', status='400').inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refund processing error: {str(e)}"
        )
    
    # Update payment status
    updated_payment = crud.update_payment_status(
        db=db,
        payment_id=payment.id,
        status=PaymentStatus.REFUNDED
    )
    
    # Update member's remaining months
    member = crud.get_member(db, payment.member_id)
    if member:
        member.remaining_months = max(0, member.remaining_months - payment.months)
        # Create refund notification
        notification = Notification(
            member_id=payment.member_id,
            type=NotificationType.EMAIL,
            status=NotificationStatus.PENDING,
            message=f"Your payment has been refunded. {payment.months} months have been removed from your membership."
        )
        db.add(notification)
        db.commit()
    
    logger.info(f"Refund processed successfully for payment {payment_id}")
    PAYMENT_REQUESTS.labels(endpoint='refund', status='200').inc()
    duration = time.time() - start_time
    logger.info(f"Refund processing took {duration:.2f} seconds")
    
    return {"status": "success", "refund_id": refund.id}