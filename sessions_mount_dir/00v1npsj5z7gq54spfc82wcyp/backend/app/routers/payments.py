from datetime import timedelta
from sqlalchemy.orm import joinedload
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query
from datetime import datetime
from sqlalchemy import func
from sqlalchemy import case
from ..services.payment_validation import validate_payment
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Payment, Member
from ..schemas import PaymentCreate, PaymentResponse

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"]
)


@router.get("/", response_model=List[PaymentResponse])
def get_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    member_id: int = Query(None),
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    db: Session = Depends(get_db)
):
    """
    获取支付记录 (支持分页和过滤)
    - member_id: 按会员ID过滤
    - start_date/end_date: 按日期范围过滤
    """
    query = db.query(Payment)
    
    if member_id:
        query = query.filter(Payment.member_id == member_id)
    if start_date:
        query = query.filter(Payment.payment_date >= start_date)
    if end_date:
        query = query.filter(Payment.payment_date <= end_date)
        
    return query.offset(skip).limit(limit).all()


@router.post("/", response_model=PaymentResponse)
def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    """
    创建新的支付记录
    """
    # 检查会员是否存在
    db_member = db.query(Member).filter(Member.id == payment.member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    db_payment = Payment(
        member_id=payment.member_id,
        amount=payment.amount,
        payment_type=payment.payment_type
    )
    
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment


@router.get("/report")
def generate_payment_report(db: Session = Depends(get_db)):
    """
    生成支付报表
    """
    # 这里可以添加更复杂的报表逻辑
    total_payments = db.query(Payment).count()
    total_amount = db.query(func.sum(Payment.amount)).scalar() or 0
    
    return {
        "total_payments": total_payments,
        "total_amount": float(total_amount),
        "report_date": datetime.now().isoformat()
    }

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
@router.get("/", response_model=List[PaymentResponse])
def get_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    member_id: int = Query(None),
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    db: Session = Depends(get_db)
):
    """
    获取支付记录 (支持分页和过滤)
    - member_id: 按会员ID过滤
    - start_date/end_date: 按日期范围过滤
    """
    # 使用缓存查询优化性能
    query = db.query(Payment).options(
        joinedload(Payment.member)
    ).execution_options(
        populate_existing=True,
        autoflush=False
    )

    if member_id:
        query = query.filter(Payment.member_id == member_id)
    if start_date:
        query = query.filter(Payment.payment_date >= start_date)
    if end_date:
        query = query.filter(Payment.payment_date <= end_date)

    return query.offset(skip).limit(limit).all()

# [AUTO-APPENDED] Failed to replace, adding new code:
@router.post("/", response_model=PaymentResponse)
def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    """
    创建新的支付记录
    """
    # 检查会员是否存在
    db_member = db.query(Member).filter(Member.id == payment.member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")

    # 验证支付数据
    validate_payment(payment)
    
    db_payment = Payment(
        member_id=payment.member_id,
        amount=payment.amount,
        payment_type=payment.payment_type,
        created_at=datetime.utcnow()
    )

    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment

# [AUTO-APPENDED] Failed to replace, adding new code:
@router.get("/report")
def generate_payment_report(db: Session = Depends(get_db)):
    """
    生成支付报表
    """
    # 使用缓存查询提高性能
    total_payments = db.query(Payment).with_entities(func.count()).scalar()
    total_amount = db.query(Payment).with_entities(func.sum(Payment.amount)).scalar() or 0
    
    # 获取最近30天的支付数据
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_payments = db.query(Payment).filter(Payment.created_at >= thirty_days_ago).count()

    return {
        "total_payments": total_payments,
        "total_amount": float(total_amount),
        "recent_payments": recent_payments,
        "report_date": datetime.utcnow().isoformat()
    }

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
@router.get("/", response_model=List[PaymentResponse])
def get_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    member_id: int = Query(None),
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    db: Session = Depends(get_db)
):
    """
    获取支付记录 (支持分页和过滤)
    - member_id: 按会员ID过滤
    - start_date/end_date: 按日期范围过滤
    """
    # 使用缓存查询优化性能
    query = db.query(Payment).options(
        joinedload(Payment.member)
    ).execution_options(
        populate_existing=True,
        autoflush=False
    )

    if member_id:
        query = query.filter(Payment.member_id == member_id)
    if start_date:
        query = query.filter(Payment.payment_date >= start_date)
    if end_date:
        query = query.filter(Payment.payment_date <= end_date)

    return query.offset(skip).limit(limit).all()

# [AUTO-APPENDED] Failed to replace, adding new code:
@router.post("/", response_model=PaymentResponse)
def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    """
    创建新的支付记录
    """
    # 检查会员是否存在
    db_member = db.query(Member).filter(Member.id == payment.member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")

    # 验证支付数据
    validate_payment(payment)

    db_payment = Payment(
        member_id=payment.member_id,
        amount=payment.amount,
        payment_type=payment.payment_type,
        created_at=datetime.utcnow()
    )

    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment

# [AUTO-APPENDED] Failed to replace, adding new code:
@router.get("/report")
def generate_payment_report(db: Session = Depends(get_db)):
    """
    生成支付报表
    """
    # 使用缓存查询提高性能
    total_payments = db.query(Payment).with_entities(func.count()).scalar()
    total_amount = db.query(Payment).with_entities(func.sum(Payment.amount)).scalar() or 0

    # 获取最近30天的支付数据
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_payments = db.query(Payment).filter(Payment.created_at >= thirty_days_ago).count()

    return {
        "total_payments": total_payments,
        "total_amount": float(total_amount),
        "recent_payments": recent_payments,
        "report_date": datetime.utcnow().isoformat()
    }