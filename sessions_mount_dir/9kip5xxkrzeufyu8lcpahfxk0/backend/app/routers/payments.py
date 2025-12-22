from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..schemas.payments import (
    PaymentCreate,
    PaymentUpdate,
    Payment,
    PaymentQuery,
    PaymentStatus,
    PaymentMethod,
    FeeType
)
from ..database import get_db
from ..models.payment import Payment as PaymentModel

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=Payment, status_code=status.HTTP_201_CREATED)
def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    """
    创建支付记录
    """
    from datetime import datetime
    from ..models.payment import Payment as PaymentModel
    
    db_payment = PaymentModel(
        amount=payment.amount,
        method=payment.method,
        fee_type=payment.fee_type,
        transaction_id=payment.transaction_id,
        payer_id=payment.payer_id,
        payer_type=payment.payer_type,
        description=payment.description,
        related_id=payment.related_id,
        status=PaymentStatus.PENDING,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    
    return db_payment


@router.get("/", response_model=List[Payment])
def list_payments(query: PaymentQuery = Depends(), db: Session = Depends(get_db)):
    """
    查询支付记录
    """
    from ..models.payment import Payment as PaymentModel
    from sqlalchemy import and_
    
    filters = []
    if query.payer_id:
        filters.append(PaymentModel.payer_id == query.payer_id)
    if query.payer_type:
        filters.append(PaymentModel.payer_type == query.payer_type)
    if query.status:
        filters.append(PaymentModel.status == query.status)
    if query.method:
        filters.append(PaymentModel.method == query.method)
    if query.fee_type:
        filters.append(PaymentModel.fee_type == query.fee_type)
    if query.start_date:
        filters.append(PaymentModel.created_at >= query.start_date)
    if query.end_date:
        filters.append(PaymentModel.created_at <= query.end_date)
    if query.related_id:
        filters.append(PaymentModel.related_id == query.related_id)
    
    offset = (query.page - 1) * query.page_size
    payments = db.query(PaymentModel).filter(and_(*filters))\
        .offset(offset).limit(query.page_size).all()
    
    return payments


@router.get("/{payment_id}", response_model=Payment)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    """
    获取单个支付记录
    """
    from ..models.payment import Payment as PaymentModel
    
    payment = db.query(PaymentModel).filter(PaymentModel.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    return payment


@router.put("/{payment_id}", response_model=Payment)
def update_payment(payment_id: int, payment: PaymentUpdate, db: Session = Depends(get_db)):
    """
    更新支付记录
    """
    from ..models.payment import Payment as PaymentModel
    from datetime import datetime
    
    db_payment = db.query(PaymentModel).filter(PaymentModel.id == payment_id).first()
    if not db_payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    if payment.status:
        db_payment.status = payment.status
    if payment.transaction_id:
        db_payment.transaction_id = payment.transaction_id
    if payment.description:
        db_payment.description = payment.description
    
    db_payment.updated_at = datetime.now()
    
    db.commit()
    db.refresh(db_payment)
    
    return db_payment
