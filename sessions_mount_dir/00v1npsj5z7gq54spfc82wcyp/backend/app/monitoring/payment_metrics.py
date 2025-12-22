from fastapi import Depends
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from typing import Optional
from datetime import datetime
from datetime import timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models.payment import Payment

# Payment metrics
PAYMENT_COUNTER = Counter(
    'payment_processed_total',
    'Total number of processed payments',
    ['payment_type']
)

PAYMENT_AMOUNT = Gauge(
    'payment_amount',
    'Amount of processed payments',
    ['payment_type']
)

PAYMENT_LATENCY = Histogram(
    'payment_processing_latency_seconds',
    'Payment processing latency in seconds'
)

PAYMENT_FAILURES = Counter(
    'payment_failures_total',
    'Total number of failed payment attempts'
)

PAYMENT_METHODS = Counter(
    'payment_methods_total',
    'Total payments by payment method',
    ['method']
)

# Subscription metrics
SUBSCRIPTION_RENEWALS = Counter(
    'subscription_renewals_total',
    'Total number of subscription renewals'
)

SUBSCRIPTION_EXPIRATIONS = Gauge(
    'subscription_expiring_total',
    'Number of subscriptions expiring soon'
)

PAYMENT_REVENUE = Gauge(
PAYMENT_REFUNDS = Counter(
    'payment_refunds_total',
    'Total number of payment refunds',
    ['payment_type']
)

PAYMENT_DISCOUNTS = Counter(
    'payment_discounts_total',
    'Total number of discounted payments',
    ['discount_type']
)

PAYMENT_REVENUE_BY_DAY = Gauge(
    'payment_revenue_daily_total',
    'Daily revenue by payment type',
    ['payment_type', 'day_of_week']
)
    'payment_revenue_total',
    'Total revenue by payment type',
    ['payment_type']
)

def record_payment(payment_type: str, amount: float, duration: Optional[float] = None):
    """
    Record payment metrics
    Args:
        payment_type: Type of payment (membership, course, etc.)
        amount: Payment amount
        duration: Processing time in seconds (optional)
    """
    PAYMENT_COUNTER.labels(payment_type=payment_type).inc()
    PAYMENT_AMOUNT.labels(payment_type=payment_type).set(amount)
    
    if duration is not None:
        PAYMENT_LATENCY.observe(duration)

def record_payment_failure():
    """Record a failed payment attempt"""
    PAYMENT_FAILURES.inc()

def record_payment_method(method: str):
def record_payment_refund(payment_type: str):
    """
    Record a payment refund
    Args:
        payment_type: Type of payment being refunded
    """
    PAYMENT_REFUNDS.labels(payment_type=payment_type).inc()

def record_payment_discount(discount_type: str):
    """
    Record a payment discount
    Args:
        discount_type: Type of discount applied
    """
    PAYMENT_DISCOUNTS.labels(discount_type=discount_type).inc()
    """
    Record payment method usage
    Args:
        method: Payment method (credit_card, wechat, alipay, etc.)
    """
    PAYMENT_METHODS.labels(method=method).inc()

def record_subscription_renewal():
    """Record a subscription renewal"""
    SUBSCRIPTION_RENEWALS.inc()

def update_expiring_subscriptions(db: Session = Depends(get_db)):
def update_daily_revenue_metrics(db: Session = Depends(get_db)):
    """
    Update daily revenue metrics by payment type
    Args:
        db: Database session
    """
    # Get current day of week (0=Monday, 6=Sunday)
    day_of_week = datetime.utcnow().weekday()
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    # Query revenue by payment type for today
    results = db.query(
        Payment.payment_type,
        func.sum(Payment.amount).label('total_amount')
    ).filter(
        func.date(Payment.payment_date) == func.current_date()
    ).group_by(Payment.payment_type).all()
    
    # Update metrics
    for payment_type, amount in results:
        PAYMENT_REVENUE_BY_DAY.labels(
            payment_type=payment_type,
            day_of_week=days[day_of_week]
        ).set(amount or 0)
    """
    Update metric for subscriptions expiring soon (within 7 days)
    Args:
        db: Database session
    """
    # Query for subscriptions expiring within 7 days
    expiring_count = db.query(Payment).filter(
        Payment.payment_type == 'membership',
        Payment.payment_date <= datetime.utcnow() + timedelta(days=7)
    ).count()
    
    SUBSCRIPTION_EXPIRATIONS.set(expiring_count)

def get_metrics(db: Session = Depends(get_db)):
    """
    Return all metrics in Prometheus format
    Args:
        db: Database session (optional)
    """
    # Update dynamic metrics before generating report
    update_expiring_subscriptions(db)
    update_daily_revenue_metrics(db)
    
    return generate_latest()