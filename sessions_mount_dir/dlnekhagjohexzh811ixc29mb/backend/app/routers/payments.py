from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Payment
from ..schemas import PaymentCreate, Payment as PaymentSchema, PaymentUpdate

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"]
)


@router.get("/", response_model=List[PaymentSchema])
def list_payments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve a list of all payments
    """
    payments = db.query(Payment).offset(skip).limit(limit).all()
    return payments


@router.post("/", response_model=PaymentSchema)
def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    """
    Create a new payment record
    """
    db_payment = Payment(**payment.dict())
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment


@router.get("/{payment_id}", response_model=PaymentSchema)
@router.put("/{payment_id}", response_model=PaymentSchema)
def update_payment(payment_id: int, payment_update: PaymentUpdate, db: Session = Depends(get_db)):
    """
    Update payment details
    """
    db_payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not db_payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    
    update_data = payment_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_payment, key, value)
    
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment(payment_id: int, db: Session = Depends(get_db)):
    """
    Delete a payment record
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    
    db.delete(payment)
    db.commit()
    return None
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    """
    Get details of a specific payment
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment