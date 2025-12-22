from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Payment, Member
from ..schemas.payment import PaymentCreate, PaymentSchema

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"]
)

@router.get("/", response_model=List[PaymentSchema])
def list_payments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    获取所有支付记录
    
    Args:
        skip: 跳过的记录数
        limit: 返回的最大记录数
        
    Returns:
        List[PaymentSchema]: 支付记录列表
        
    Raises:
        HTTPException: 如果数据库查询失败
    """
    try:
        payments = db.query(Payment).offset(skip).limit(limit).all()
        return payments
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch payments: {str(e)}"
        )

@router.post("/", response_model=PaymentSchema)
def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    """
    创建新的支付记录
    """
    # 检查会员是否存在
    member = db.query(Member).filter(Member.id == payment.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    db_payment = Payment(
        member_id=payment.member_id,
        amount=payment.amount,
        payment_date=payment.payment_date,
        payment_method=payment.payment_method
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment

@router.get("/{payment_id}", response_model=PaymentSchema)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    """
    根据ID获取支付记录
    
    Args:
        payment_id: 支付记录ID
        
    Returns:
        PaymentSchema: 支付记录详情
        
    Raises:
        HTTPException: 
            - 404: 如果支付记录不存在
            - 500: 如果数据库查询失败
    """
    try:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        return payment
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch payment: {str(e)}"
        )