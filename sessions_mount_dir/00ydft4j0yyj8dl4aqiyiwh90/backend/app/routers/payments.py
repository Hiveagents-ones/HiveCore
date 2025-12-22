from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Payment, Member
from ..schemas import PaymentCreate, PaymentResponse

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"]
)


@router.get("/", response_model=List[PaymentResponse], status_code=200)
def get_payments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    获取所有支付记录
    :param skip: 跳过记录数
    :param limit: 限制返回记录数
    :param db: 数据库会话
    :return: 支付记录列表
    """
    payments = db.query(Payment).offset(skip).limit(limit).all()
    return payments


@router.post("/", response_model=PaymentResponse, status_code=201)
def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    """
    创建支付记录
    :param payment: 支付信息
    :param db: 数据库会话
    :return: 创建的支付记录
    """
    # 检查会员是否存在
    db_member = db.query(Member).filter(Member.id == payment.member_id).first()
    if not db_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member with id {payment.member_id} not found"
        )

    db_payment = Payment(
        member_id=payment.member_id,
        amount=payment.amount,
        payment_method=payment.payment_method
    )

    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment


@router.get("/{payment_id}", response_model=PaymentResponse, status_code=200)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    """
    获取单个支付记录
    :param payment_id: 支付记录ID
    :param db: 数据库会话
    :return: 支付记录
    """
    db_payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not db_payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with id {payment_id} not found"
        )
    return db_payment