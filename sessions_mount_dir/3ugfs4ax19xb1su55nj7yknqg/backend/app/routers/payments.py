from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Payment
from ..schemas import PaymentCreate, Payment as PaymentSchema

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
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    """
    Get details of a specific payment
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment