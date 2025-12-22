from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer()
from ..auth.auth_handler import decodeJWT
from sqlalchemy.orm import Session

from ..schemas.payment import Payment, PaymentCreate, PaymentUpdate
from ..database import get_db
from ..models.audit_log import AuditLog

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"],
    dependencies=[Security(HTTPBearer())]
)


@router.post("/", response_model=Payment)
def create_payment(
    payment: PaymentCreate, 
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """
    Create a new payment record.
    """
    token = decodeJWT(credentials.credentials)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = token.get("user_id")
    db_payment = Payment(
    token = decodeJWT(credentials.credentials)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = token.get("user_id")
        member_id=payment.member_id,
        amount=payment.amount,
        payment_method=payment.payment_method,
        payment_date=datetime.now()
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    # Create audit log
    audit_log = AuditLog(
        action="CREATE_PAYMENT",
        table_name="payments",
        record_id=db_payment.id,
        changed_by=user_id,
        old_values={},
        new_values={
            "member_id": payment.member_id,
            "amount": payment.amount,
            "payment_method": payment.payment_method
        }
    )
    db.add(audit_log)
    db.commit()
    return db_payment


@router.get("/", response_model=List[Payment])
def read_payments(
    skip: int = 0, 
    limit: int = 100, 
    member_id: int = None,
    payment_method: str = None,
    start_date: datetime = None,
    end_date: datetime = None,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """
    Retrieve payments with pagination and filtering.
    """
    token = decodeJWT(credentials.credentials)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")

    query = db.query(Payment)
    
    if member_id:
        query = query.filter(Payment.member_id == member_id)
    if payment_method:
        query = query.filter(Payment.payment_method == payment_method)
    if start_date:
        query = query.filter(Payment.payment_date >= start_date)
    if end_date:
        query = query.filter(Payment.payment_date <= end_date)
        
    return query.offset(skip).limit(limit).all()


@router.get("/{payment_id}", response_model=Payment)
def read_payment(
    payment_id: int, 
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """
    Get a specific payment by ID.
    """
    token = decodeJWT(credentials.credentials)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    db_payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if db_payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return db_payment


@router.put("/{payment_id}", response_model=Payment)
def update_payment(
    payment_id: int, 
    payment: PaymentUpdate, 
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """
    Update a payment record.
    token = decodeJWT(credentials.credentials)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = token.get("user_id")
    """
    db_payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if db_payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if payment.amount is not None:
        db_payment.amount = payment.amount
    if payment.payment_method is not None:
        db_payment.payment_method = payment.payment_method
    
    # Create audit log
    old_values = {
        "amount": db_payment.amount,
        "payment_method": db_payment.payment_method
    }
    
    audit_log = AuditLog(
        action="UPDATE_PAYMENT",
        table_name="payments",
        record_id=payment_id,
        changed_by=user_id,
        old_values=old_values,
        new_values=payment.dict(exclude_unset=True)
    )
    db.add(audit_log)
    
    db.commit()
    db.refresh(db_payment)
    return db_payment


@router.delete("/{payment_id}", response_model=Payment)
def delete_payment(
    payment_id: int, 
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """
    Delete a payment record.
    token = decodeJWT(credentials.credentials)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = token.get("user_id")
    """
    db_payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if db_payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    db.delete(db_payment)
    # Create audit log
    audit_log = AuditLog(
        action="DELETE_PAYMENT",
        table_name="payments",
        record_id=payment_id,
        changed_by=user_id,
        old_values={
            "member_id": db_payment.member_id,
            "amount": db_payment.amount,
            "payment_method": db_payment.payment_method
        },
        new_values={}
    )
    db.add(audit_log)
    db.commit()
    return db_payment

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    query = db.query(Payment)

    if member_id is not None:
        query = query.filter(Payment.member_id == member_id)
    if payment_method is not None:
        query = query.filter(Payment.payment_method == payment_method)
    if start_date is not None:
        query = query.filter(Payment.payment_date >= start_date)
    if end_date is not None:
        query = query.filter(Payment.payment_date <= end_date)