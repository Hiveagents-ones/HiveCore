from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .... import crud, schemas
from ....database import get_db

router = APIRouter()

@router.post("/", response_model=schemas.PaymentRecord, status_code=status.HTTP_201_CREATED)
def create_payment(payment: schemas.PaymentRecordCreate, db: Session = Depends(get_db)):
    """
    Create a new payment record for a member.
    """
    # Verify member exists
    db_member = crud.get_member(db, member_id=payment.member_id)
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    return crud.create_payment_record(db=db, payment=payment)

@router.get("/{payment_id}", response_model=schemas.PaymentRecord)
def read_payment(payment_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a specific payment record by ID.
    """
    db_payment = crud.get_payment_record(db, payment_id=payment_id)
    if db_payment is None:
        raise HTTPException(status_code=404, detail="Payment record not found")
    return db_payment

@router.get("/member/{member_id}", response_model=List[schemas.PaymentRecord])
def read_payments_by_member(member_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve all payment records for a specific member.
    """
    # Verify member exists
    db_member = crud.get_member(db, member_id=member_id)
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    payments = crud.get_payment_records_by_member(db, member_id=member_id, skip=skip, limit=limit)
    return payments

@router.get("/", response_model=List[schemas.PaymentRecord])
def read_all_payments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve all payment records with pagination.
    """
    payments = crud.get_all_payment_records(db, skip=skip, limit=limit)
    return payments

@router.put("/{payment_id}", response_model=schemas.PaymentRecord)
def update_payment(payment_id: int, payment: schemas.PaymentRecordUpdate, db: Session = Depends(get_db)):
    """
    Update a payment record.
    """
    db_payment = crud.update_payment_record(db, payment_id=payment_id, payment=payment)
    if db_payment is None:
        raise HTTPException(status_code=404, detail="Payment record not found")
    return db_payment

@router.delete("/{payment_id}", response_model=schemas.PaymentRecord)
def delete_payment(payment_id: int, db: Session = Depends(get_db)):
    """
    Delete a payment record.
    """
    db_payment = crud.delete_payment_record(db, payment_id=payment_id)
    if db_payment is None:
        raise HTTPException(status_code=404, detail="Payment record not found")
    return db_payment
