from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..models.payments import Payment, MembershipCard, BillingRecord
from ..schemas.payments import PaymentCreate, PaymentUpdate
from ..database import get_db

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=Payment, status_code=status.HTTP_201_CREATED)
async def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    """
    Create a new payment record
    """
    try:
        db_payment = Payment(**payment)
        db.add(db_payment)
        db.commit()
        db.refresh(db_payment)
        return db_payment
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating payment: {str(e)}"
        )


@router.get("/", response_model=List[Payment])
async def get_payments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get all payment records with pagination
    """
    return db.query(Payment).offset(skip).limit(limit).all()


@router.get("/{payment_id}", response_model=Payment)
async def get_payment(payment_id: int, db: Session = Depends(get_db)):
    """
    Get a specific payment by ID
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with id {payment_id} not found"
        )
    return payment


@router.get("/members/{member_id}", response_model=List[Payment])
async def get_member_payments(member_id: int, db: Session = Depends(get_db)):
    """
    Get all payments for a specific member
    """
    payments = db.query(Payment).filter(Payment.member_id == member_id).all()
    if not payments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No payments found for member with id {member_id}"
        )
    return payments


@router.put("/{payment_id}/status", response_model=Payment)
@router.put("/{payment_id}", response_model=Payment)
async def update_payment(payment_id: int, payment: PaymentUpdate, db: Session = Depends(get_db)):
    """
    Update payment details
    """
    db_payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not db_payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with id {payment_id} not found"
        )

    try:
        update_data = payment.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_payment, key, value)
        db.commit()
        db.refresh(db_payment)
        return db_payment
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating payment: {str(e)}"
        )
async def update_payment_status(payment_id: int, status_update: dict, db: Session = Depends(get_db)):
    """
    Update payment status
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with id {payment_id} not found"
        )
    
    try:
        payment.status = status_update.get("status", payment.status)
        payment.processed_at = status_update.get("processed_at", payment.processed_at)
        db.commit()
        db.refresh(payment)
        return payment
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating payment status: {str(e)}"
        )


@router.get("/members/{member_id}/cards", response_model=List[MembershipCard])
async def get_member_cards(member_id: int, db: Session = Depends(get_db)):
    """
    Get all membership cards for a specific member
    """
    cards = db.query(MembershipCard).filter(MembershipCard.member_id == member_id).all()
    if not cards:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No membership cards found for member with id {member_id}"
        )
    return cards


@router.get("/members/{member_id}/billing", response_model=List[BillingRecord])
@router.get("/summary/{member_id}", response_model=dict)
async def get_payment_summary(member_id: int, db: Session = Depends(get_db)):
    """
    Get payment summary for a member including:
    - Total payments
    - Last payment date
    - Outstanding balance
    """
    payments = db.query(Payment).filter(Payment.member_id == member_id).all()
    if not payments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No payments found for member with id {member_id}"
        )
    
    total_amount = sum(p.amount for p in payments)
    last_payment = max(p.payment_date for p in payments)
    
    # Calculate outstanding balance from billing records
    billing_records = db.query(BillingRecord).filter(BillingRecord.member_id == member_id).all()
    billed_amount = sum(r.amount for r in billing_records)
    outstanding = billed_amount - total_amount
    
    return {
        "total_payments": len(payments),
        "total_amount": total_amount,
        "last_payment_date": last_payment,
        "outstanding_balance": outstanding if outstanding > 0 else 0
    }
async def get_member_billing_records(member_id: int, db: Session = Depends(get_db)):
    """
    Get all billing records for a specific member
    """
    records = db.query(BillingRecord).filter(BillingRecord.member_id == member_id).all()
    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No billing records found for member with id {member_id}"
        )
    return records