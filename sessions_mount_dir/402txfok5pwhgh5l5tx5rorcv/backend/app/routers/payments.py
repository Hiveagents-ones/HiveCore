from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import schemas, models, core.payment
from ..database import get_db

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"]
)

@router.post("/", response_model=schemas.Payment)
def create_payment(
    payment: schemas.PaymentCreate,
    db: Session = Depends(get_db)
):
    """
    创建支付订单
    """
    # 验证会员是否存在
    member = db.query(models.Member).filter(models.Member.id == payment.member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # 创建支付记录
    db_payment = models.Payment(
        member_id=payment.member_id,
        amount=payment.amount,
        type=payment.type,
        status=schemas.PaymentStatus.PENDING,
        description=payment.description
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    
    # 调用支付核心处理
    try:
        payment_result = core.payment.create_payment(
            payment_id=db_payment.id,
            amount=payment.amount,
            payment_type=payment.type,
            description=payment.description
        )
        
        # 更新支付记录
        db_payment.transaction_id = payment_result.get("transaction_id")
        db_payment.status = schemas.PaymentStatus.PENDING
        db.commit()
        
        return db_payment
    except Exception as e:
        # 支付创建失败，更新状态
        db_payment.status = schemas.PaymentStatus.FAILED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment creation failed: {str(e)}"
        )

@router.post("/callback/{payment_provider}")
def payment_callback(
    payment_provider: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    处理支付回调
    """
    try:
        # 获取回调数据
        callback_data = request.json()
        
        # 验证并处理回调
        result = core.payment.handle_callback(
            provider=payment_provider,
            callback_data=callback_data
        )
        
        # 更新支付记录
        payment_id = result.get("payment_id")
        payment_status = result.get("status")
        
        db_payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
        if not db_payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        db_payment.status = payment_status
        db.commit()
        
        return {"status": "success", "payment_id": payment_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Callback processing failed: {str(e)}"
        )

@router.get("/", response_model=List[schemas.Payment])
def list_payments(
    member_id: Optional[int] = Query(None, description="会员ID"),
    payment_type: Optional[schemas.PaymentType] = Query(None, description="支付类型"),
    status: Optional[schemas.PaymentStatus] = Query(None, description="支付状态"),
    start_date: Optional[str] = Query(None, description="开始日期(YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期(YYYY-MM-DD)"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    db: Session = Depends(get_db)
):
    """
    查询支付记录
    支持按会员ID、支付类型、状态和日期范围过滤
    """
    query = db.query(models.Payment)

    # 日期范围过滤
    if start_date:
        query = query.filter(models.Payment.created_at >= start_date)
    if end_date:
        query = query.filter(models.Payment.created_at <= end_date)
    
    if member_id:
        query = query.filter(models.Payment.member_id == member_id)
    if payment_type:
        query = query.filter(models.Payment.type == payment_type)
    if status:
        query = query.filter(models.Payment.status == status)
    
    payments = query.offset(skip).limit(limit).all()
    return payments

@router.get("/{payment_id}", response_model=schemas.Payment)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db)
):
    """
    获取单个支付记录
    """
    payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    return payment

@router.post("/{payment_id}/refund")
def refund_payment(
    payment_id: int,
    refund_amount: Optional[float] = Query(None, description="退款金额，不填则全额退款"),
    reason: Optional[str] = Query(None, description="退款原因"),
    db: Session = Depends(get_db)
):
    """
    退款处理
    """
    payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    if payment.status != schemas.PaymentStatus.SUCCESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only successful payments can be refunded"
        )
    
    try:
        # 确定退款金额
        amount_to_refund = refund_amount if refund_amount is not None else payment.amount
        
        if amount_to_refund > payment.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refund amount cannot exceed payment amount"
            )
        
        # 调用支付核心处理退款
        refund_result = core.payment.process_refund(
            payment_id=payment_id,
            amount=amount_to_refund,
            transaction_id=payment.transaction_id,
            reason=reason
        )
        
        # 更新支付状态
        if amount_to_refund == payment.amount:
            payment.status = schemas.PaymentStatus.REFUNDED
        else:
            payment.status = schemas.PaymentStatus.PARTIAL_REFUNDED
        payment.refund_amount = amount_to_refund
        payment.refund_reason = reason
        db.commit()
        
        return {"status": "success", "refund_id": refund_result.get("refund_id")}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refund failed: {str(e)}"
        )


@router.get("/statistics", response_model=dict)
def get_payment_statistics(
    start_date: Optional[str] = Query(None, description="开始日期(YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期(YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    获取支付统计数据
    """
    query = db.query(models.Payment)
    
    if start_date:
        query = query.filter(models.Payment.created_at >= start_date)
    if end_date:
        query = query.filter(models.Payment.created_at <= end_date)
    
    # 总支付金额
    total_amount = db.query(func.sum(models.Payment.amount)).filter(
        models.Payment.status == schemas.PaymentStatus.SUCCESS
    ).scalar() or 0
    
    # 按类型统计
    type_stats = db.query(
        models.Payment.type,
        func.count(models.Payment.id).label('count'),
        func.sum(models.Payment.amount).label('total')
    ).filter(
        models.Payment.status == schemas.PaymentStatus.SUCCESS
    ).group_by(models.Payment.type).all()
    
    # 按状态统计
    status_stats = db.query(
        models.Payment.status,
        func.count(models.Payment.id).label('count')
    ).group_by(models.Payment.status).all()
    
    return {
        "total_amount": float(total_amount),
        "by_type": [{"type": t.type, "count": t.count, "total": float(t.total)} for t in type_stats],
        "by_status": [{"status": s.status, "count": s.count} for s in status_stats]
    }