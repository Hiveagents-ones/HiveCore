from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime

from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/payment",
    tags=["payment"]
)

def update_membership_expiry(member_id: int, package_duration_days: int, db: Session):
    """更新会员到期时间"""
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        return
    
    if member.expires_at and member.expires_at > datetime.utcnow():
        # 如果会员还未到期，在现有时间基础上延长
        new_expiry = member.expires_at + timedelta(days=package_duration_days)
    else:
        # 如果会员已过期或没有到期时间，从当前时间开始计算
        new_expiry = datetime.utcnow() + timedelta(days=package_duration_days)
    
    member.expires_at = new_expiry
    db.commit()

def send_notification(member_id: int, message: str):
    """发送通知（模拟实现）"""
    # 这里可以集成邮件、短信或其他通知服务
    print(f"Sending notification to member {member_id}: {message}")

@router.post("/callback/{payment_method}")
def handle_payment_callback(
    payment_method: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    处理支付回调
    """
    # 根据不同的支付方式获取回调数据
    if payment_method == "alipay":
        callback_data = await request.json()
        # 这里应该验证支付宝的签名
        payment_id = callback_data.get("out_trade_no")
        trade_status = callback_data.get("trade_status")
        
        if trade_status == "TRADE_SUCCESS":
            payment_status = "success"
        elif trade_status == "TRADE_CLOSED":
            payment_status = "failed"
        else:
            payment_status = "pending"
            
    elif payment_method == "wechat":
        callback_data = await request.json()
        # 这里应该验证微信的签名
        payment_id = callback_data.get("out_trade_no")
        result_code = callback_data.get("result_code")
        
        if result_code == "SUCCESS":
            payment_status = "success"
        else:
            payment_status = "failed"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported payment method"
        )
    
    # 查找支付记录
    payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # 更新支付状态
    payment.status = payment_status
    payment.paid_at = datetime.utcnow() if payment_status == "success" else None
    
    # 更新订单状态
    order = payment.order
    if payment_status == "success":
        order.status = "paid"
        order.paid_at = datetime.utcnow()
        
        # 获取套餐信息
        package = db.query(models.Package).filter(models.Package.id == order.package_id).first()
        
        # 更新会员到期时间
        background_tasks.add_task(
            update_membership_expiry,
            member_id=order.member_id,
            package_duration_days=package.duration_days,
            db=db
        )
        
        # 发送确认通知
        background_tasks.add_task(
            send_notification,
            member_id=order.member_id,
            message=f"Payment successful! Your membership has been extended."
        )
    elif payment_status == "failed":
        order.status = "failed"
    
    db.commit()
    
    return {"status": "ok", "payment_status": payment_status}

@router.get("/status/{payment_id}", response_model=schemas.PaymentStatusResponse)
def get_payment_status(
    payment_id: int,
    db: Session = Depends(get_db)
):
    """
    查询支付状态
    """
    payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    return schemas.PaymentStatusResponse(
        payment_id=payment.id,
        order_id=payment.order_id,
        status=payment.status,
        amount=payment.amount,
        payment_method=payment.payment_method,
        created_at=payment.created_at,
        paid_at=payment.paid_at
    )

@router.post("/verify/{payment_id}", response_model=schemas.PaymentVerificationResponse)
def verify_payment(
    payment_id: int,
    db: Session = Depends(get_db)
):
    """
    验证支付结果（主动查询）
    """
    payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # 这里应该根据支付方式调用相应的支付网关API查询实际支付状态
    # 模拟实现：假设支付成功
    if payment.status == "pending":
        # 实际项目中，这里应该调用支付宝/微信的查询接口
        # 模拟支付成功
        payment.status = "success"
        payment.paid_at = datetime.utcnow()
        
        # 更新订单状态
        order = payment.order
        order.status = "paid"
        order.paid_at = datetime.utcnow()
        
        # 获取套餐信息
        package = db.query(models.Package).filter(models.Package.id == order.package_id).first()
        
        # 更新会员到期时间
        update_membership_expiry(
            member_id=order.member_id,
            package_duration_days=package.duration_days,
            db=db
        )
        
        # 发送确认通知
        send_notification(
            member_id=order.member_id,
            message=f"Payment verified! Your membership has been extended."
        )
        
        db.commit()
    
    return schemas.PaymentVerificationResponse(
        payment_id=payment.id,
        is_verified=payment.status == "success",
        status=payment.status,
        message="Payment verified successfully" if payment.status == "success" else "Payment is pending or failed"
    )
