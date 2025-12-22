from decimal import Decimal
from decimal import ROUND_HALF_UP
from datetime import datetime
from datetime import timedelta
from typing import Optional

from fastapi import HTTPException, status
from pydantic import BaseModel, validator

from .database import get_db
from sqlalchemy import func
from .models import Payment, Member, Course


class PaymentValidationError(Exception):
    """Custom exception for payment validation errors"""
    pass


class PaymentRequest(BaseModel):
    """Pydantic model for validating payment requests"""
    member_id: int
    amount: Decimal
    payment_date: datetime
    payment_type: str
    course_id: Optional[int] = None

    @validator('amount')
    def amount_must_be_positive(cls, v):
        if v <= Decimal('0'):
            raise ValueError('Amount must be positive')
        return v

    @validator('payment_type')
    def validate_payment_type(cls, v):
        valid_types = ['membership', 'course', 'other']
        if v not in valid_types:
            raise ValueError(f'Payment type must be one of {valid_types}')
        return v


def validate_payment_request(payment_data: dict) -> PaymentRequest:
    """
    Validate payment request data
    
    Args:
        payment_data: Dictionary containing payment details
        
    Returns:
        Validated PaymentRequest object
        
    Raises:
        HTTPException: If validation fails
    """
    try:
        return PaymentRequest(**payment_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )


def validate_membership_payment(db, member_id: int, amount: Decimal) -> None:
    # Validate membership type
    member = db.query(Member).filter(Member.id == member_id).first()
    if member.membership_type == 'premium' and amount < Decimal('100'):
        raise PaymentValidationError("Premium membership requires minimum payment of 100")
    """
    Validate membership payment
    
    Args:
        db: Database session
        member_id: ID of the member
        amount: Payment amount
        
    Raises:
        PaymentValidationError: If validation fails
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise PaymentValidationError(f"Member with ID {member_id} not found")
    
    # Basic validation - could be extended with business rules
    if amount < Decimal('50'):  # Minimum membership fee
        raise PaymentValidationError("Membership payment amount is below minimum")


def validate_course_payment(db, member_id: int, course_id: int, amount: Decimal) -> None:
    # Validate course price matches
    if amount != course.price:
        raise PaymentValidationError(f"Course payment amount {amount} does not match course price {course.price}")
    """
    Validate course payment
    
    Args:
        db: Database session
        member_id: ID of the member
        course_id: ID of the course
        amount: Payment amount
        
    Raises:
        PaymentValidationError: If validation fails
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise PaymentValidationError(f"Member with ID {member_id} not found")
    
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise PaymentValidationError(f"Course with ID {course_id} not found")
    
    # Basic validation - could be extended with business rules
    if amount <= Decimal('0'):
        raise PaymentValidationError("Course payment amount must be positive")


def calculate_tax_amount(amount: Decimal, tax_rate: Decimal = Decimal('0.1')) -> Decimal:
    """
    Calculate tax amount based on the given rate
    
    Args:
        amount: Original amount
        tax_rate: Tax rate (default 10%)
        
    Returns:
        Tax amount
    """
    return (amount * tax_rate).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)


def validate_payment_duplicate(db, member_id: int, amount: Decimal, payment_date: datetime, payment_type: str) -> None:
    """
    Check for potential duplicate payments with enhanced detection logic

    Args:
        db: Database session
        member_id: ID of the member
        amount: Payment amount
        payment_date: Payment date
        payment_type: Type of payment

    Raises:
        PaymentValidationError: If duplicate is detected
    """
def validate_payment_total(db, member_id: int, payment_type: str, amount: Decimal) -> None:
    """
    Validate payment total against member's existing payments with enhanced limits
    
    Args:
        db: Database session
        member_id: ID of the member
        payment_type: Type of payment ('membership' or 'course')
        amount: Payment amount (must be positive)
        
    Raises:
        PaymentValidationError: If payment total exceeds limits
    """
    """
    Validate payment total against member's existing payments
    
    Args:
        db: Database session
        member_id: ID of the member
        payment_type: Type of payment
        amount: Payment amount
        
    Raises:
        PaymentValidationError: If payment total exceeds limits
    """
    if payment_type == 'membership':
        # Get total membership payments in current year
        current_year = datetime.now().year
        year_start = datetime(current_year, 1, 1)
        
        total = db.query(
            func.sum(Payment.amount)
        ).filter(
            Payment.member_id == member_id,
            Payment.payment_type == 'membership',
            Payment.payment_date >= year_start
        ).scalar() or Decimal('0')
        
        if total + amount > Decimal('1000'):  # Annual membership cap
            raise PaymentValidationError("Annual membership payment limit exceeded")
    elif payment_type == 'course':
        # Get total course payments in current month
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1)
        
        total = db.query(
            func.sum(Payment.amount)
        ).filter(
            Payment.member_id == member_id,
            Payment.payment_type == 'course',
            Payment.payment_date >= month_start
        ).scalar() or Decimal('0')
        
        if total + amount > Decimal('500'):  # Monthly course cap
            raise PaymentValidationError("Monthly course payment limit exceeded")
    """
    Check for potential duplicate payments
    
    Args:
        db: Database session
        member_id: ID of the member
        amount: Payment amount
        payment_date: Payment date
        
    Raises:
        PaymentValidationError: If duplicate is detected
    """
    # Check for similar payments within a short time window
    time_window = payment_date.replace(minute=payment_date.minute - 5)
    
    duplicate = db.query(Payment).filter(
        Payment.member_id == member_id,
        Payment.amount == amount,
        Payment.payment_date >= time_window
    ).first()
    
    if duplicate:
        raise PaymentValidationError("Potential duplicate payment detected")

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
def validate_course_payment(db, member_id: int, course_id: int, amount: Decimal) -> None:
    """
    Validate course payment

    Args:
        db: Database session
        member_id: ID of the member
        course_id: ID of the course
        amount: Payment amount

    Raises:
        PaymentValidationError: If validation fails
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise PaymentValidationError(f"Member with ID {member_id} not found")

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise PaymentValidationError(f"Course with ID {course_id} not found")

    # Validate course price matches
    if amount != course.price:
        raise PaymentValidationError(f"Course payment amount {amount} does not match course price {course.price}")

    # Basic validation - could be extended with business rules
    if amount <= Decimal('0'):
        raise PaymentValidationError("Course payment amount must be positive")

# [AUTO-APPENDED] Failed to replace, adding new code:
def calculate_tax_amount(amount: Decimal, tax_rate: Decimal = Decimal('0.1')) -> Decimal:
    """
    Calculate tax amount based on the given rate

    Args:
        amount: Original amount (must be positive)
        tax_rate: Tax rate (default 10%, must be between 0 and 1)

    Returns:
        Tax amount rounded to 2 decimal places

    Raises:
        ValueError: If amount or tax_rate is invalid
    """
    if amount <= Decimal('0'):
        raise ValueError("Amount must be positive")
    if tax_rate < Decimal('0') or tax_rate > Decimal('1'):
        raise ValueError("Tax rate must be between 0 and 1")
    
    return (amount * tax_rate).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
def validate_membership_payment(db, member_id: int, amount: Decimal) -> None:
    """
    Validate membership payment with enhanced rules

    Args:
        db: Database session
        member_id: ID of the member
        amount: Payment amount

    Raises:
        PaymentValidationError: If validation fails
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise PaymentValidationError(f"Member with ID {member_id} not found")

    # Membership type specific validation
    if member.membership_type == 'premium' and amount < Decimal('100'):
        raise PaymentValidationError("Premium membership requires minimum payment of 100")
    elif member.membership_type == 'basic' and amount < Decimal('50'):
        raise PaymentValidationError("Basic membership requires minimum payment of 50")

    # Validate payment amount format
    if amount.as_tuple().exponent < -2:
        raise PaymentValidationError("Payment amount can have maximum 2 decimal places")

# [AUTO-APPENDED] Failed to replace, adding new code:
def validate_payment_duplicate(db, member_id: int, amount: Decimal, payment_date: datetime, payment_type: str) -> None:
    """
    Check for potential duplicate payments with enhanced detection logic
    
    Args:
        db: Database session
        member_id: ID of the member
        amount: Payment amount
        payment_date: Payment date
        payment_type: Payment type

    Raises:
        PaymentValidationError: If duplicate is detected
    """
    # Check for similar payments within a 10-minute window
    time_window_start = payment_date - timedelta(minutes=10)
    time_window_end = payment_date + timedelta(minutes=10)

    duplicate = db.query(Payment).filter(
        Payment.member_id == member_id,
        Payment.amount == amount,
        Payment.payment_type == payment_type,
        Payment.payment_date.between(time_window_start, time_window_end)
    ).first()

    if duplicate:
        raise PaymentValidationError(
            f"Potential duplicate payment detected: {duplicate.id} on {duplicate.payment_date}"
        )