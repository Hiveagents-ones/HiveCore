from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from decimal import Decimal

from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/membership",
    tags=["membership"]
)

@router.get("/status", response_model=schemas.MembershipStatusResponse)
def get_membership_status(
    member_id: int,
    db: Session = Depends(get_db)
):
    """
    获取会员当前状态信息，包括会员详情、可用套餐和有效订单
    """
    # 获取会员信息
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # 获取可用套餐
    packages = db.query(models.Package).filter(models.Package.is_active == True).all()
    
    # 获取有效订单
    active_orders = db.query(models.Order).filter(
        models.Order.member_id == member_id,
        models.Order.status.in_(["pending", "paid"])
    ).all()
    
    return schemas.MembershipStatusResponse(
        member=member,
        available_packages=packages,
        active_orders=active_orders
    )

@router.get("/packages", response_model=List[schemas.PackageResponse])
def get_packages(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    获取会员套餐列表
    """
    query = db.query(models.Package)
    if active_only:
        query = query.filter(models.Package.is_active == True)
    
    packages = query.all()
    return packages

@router.post("/renew", response_model=schemas.RenewalResponse)
def create_renewal_order(
    renewal: schemas.RenewalRequest,
    member_id: int,
    db: Session = Depends(get_db)
):
    """
    创建续费订单
    """
    # 验证会员存在
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # 验证套餐存在且可用
    package = db.query(models.Package).filter(
        models.Package.id == renewal.package_id,
        models.Package.is_active == True
    ).first()
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found or inactive"
        )
    
    # 生成唯一订单号
    order_number = f"ORD{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{member_id}"
    
    # 创建订单
    order = models.Order(
        member_id=member_id,
        package_id=package.id,
        order_number=order_number,
        amount=package.price,
        status="pending"
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    
    # 创建支付记录
    payment = models.Payment(
        order_id=order.id,
        member_id=member_id,
        payment_method=renewal.payment_method,
        amount=package.price,
        status="pending"
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    return schemas.RenewalResponse(
        order=order,
        payment=payment,
        message="Renewal order created successfully"
    )

@router.post("/renew/{order_id}/confirm", response_model=schemas.RenewalResponse)
def confirm_renewal_payment(
    order_id: int,
    transaction_id: str,
    db: Session = Depends(get_db)
):
    """
    确认支付成功并更新会员到期时间
    """
    # 获取订单
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is not in pending status"
        )
    
    # 获取支付记录
    payment = db.query(models.Payment).filter(models.Payment.order_id == order_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment record not found"
        )
    
    # 更新支付状态
    payment.status = "success"
    payment.transaction_id = transaction_id
    db.commit()
    
    # 更新订单状态
    order.status = "paid"
    db.commit()
    
    # 更新会员到期时间
    member = db.query(models.Member).filter(models.Member.id == order.member_id).first()
    if member:
        # 计算新的到期时间
        current_expiry = member.expiry_date or datetime.utcnow()
        new_expiry = current_expiry + timedelta(days=order.package.duration_months * 30)
        member.expiry_date = new_expiry
        member.membership_level = order.package.name  # 可根据业务需求调整
        db.commit()
    
    return schemas.RenewalResponse(
        order=order,
        payment=payment,
        message="Payment confirmed and membership updated"
    )

@router.get("/orders", response_model=List[schemas.OrderResponse])
def get_member_orders(
    member_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取会员订单列表
    """
    query = db.query(models.Order).filter(models.Order.member_id == member_id)
    if status:
        query = query.filter(models.Order.status == status)
    
    orders = query.all()
    return orders

@router.get("/orders/{order_id}", response_model=schemas.OrderResponse)
def get_order_detail(
    order_id: int,
    member_id: int,
    db: Session = Depends(get_db)
):
    """
    获取订单详情
    """
    order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.member_id == member_id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return order
