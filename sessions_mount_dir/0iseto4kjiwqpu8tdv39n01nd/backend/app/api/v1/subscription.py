from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus, SubscriptionPlanType
from app.models.order import Order, OrderStatus
from app.schemas.order import OrderResponse, OrderCreate
from app.api.v1.payment import process_payment
from app.core.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/subscription", tags=["subscription"])


@router.get("/plans", response_model=List[dict])
def get_subscription_plans(db: Session = Depends(get_db)):
    """获取所有可用的订阅计划"""
    plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.is_active == True).all()
    return [
        {
            "id": plan.id,
            "name": plan.name,
            "description": plan.description,
            "type": plan.type,
            "price": float(plan.price),
            "currency": plan.currency,
            "duration_days": plan.duration_days,
            "features": plan.features
        }
        for plan in plans
    ]


@router.get("/status", response_model=dict)
def get_subscription_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的订阅状态"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == SubscriptionStatus.ACTIVE
    ).first()

    if not subscription:
        return {
            "status": "none",
            "message": "No active subscription"
        }

    return {
        "status": subscription.status,
        "plan": {
            "id": subscription.plan.id,
            "name": subscription.plan.name,
            "type": subscription.plan.type
        },
        "start_date": subscription.start_date,
        "end_date": subscription.end_date,
        "auto_renew": subscription.auto_renew,
        "days_remaining": subscription.days_remaining(),
        "is_active": subscription.is_active()
    }


@router.post("/subscribe", response_model=dict)
def subscribe(
    plan_id: int,
    payment_method: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新的订阅"""
    # 验证订阅计划
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == plan_id,
        SubscriptionPlan.is_active == True
    ).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found"
        )

    # 检查是否已有活跃订阅
    existing_subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == SubscriptionStatus.ACTIVE
    ).first()
    if existing_subscription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an active subscription"
        )

    # 创建订单
    order = Order(
        user_id=current_user.id,
        amount=float(plan.price),
        currency=plan.currency,
        status=OrderStatus.PENDING,
        payment_method=payment_method,
        is_renewal=False
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # 创建订阅记录
    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=plan.duration_days)
    
    subscription = Subscription(
        user_id=current_user.id,
        plan_id=plan.id,
        status=SubscriptionStatus.PENDING,
        start_date=start_date,
        end_date=end_date,
        auto_renew=True,
        last_payment_id=order.id
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    # 处理支付
    try:
        payment_result = process_payment(
            order_id=order.id,
            payment_method=payment_method,
            db=db
        )
        
        if payment_result["status"] == "success":
            subscription.status = SubscriptionStatus.ACTIVE
            order.status = OrderStatus.COMPLETED
            db.commit()
            
            return {
                "message": "Subscription created successfully",
                "subscription_id": subscription.id,
                "payment_status": payment_result["status"]
            }
        else:
            return {
                "message": "Payment processing",
                "subscription_id": subscription.id,
                "payment_url": payment_result.get("payment_url"),
                "payment_status": payment_result["status"]
            }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment processing failed: {str(e)}"
        )


@router.post("/renew", response_model=dict)
def renew_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """续费订阅"""
    # 获取当前活跃订阅
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == SubscriptionStatus.ACTIVE
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )

    # 创建续费订单
    order = Order(
        user_id=current_user.id,
        amount=float(subscription.plan.price),
        currency=subscription.plan.currency,
        status=OrderStatus.PENDING,
        payment_method=subscription.last_payment.payment_method if subscription.last_payment else "stripe",
        is_renewal=True,
        subscription_id=subscription.id
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # 处理支付
    try:
        payment_result = process_payment(
            order_id=order.id,
            payment_method=order.payment_method,
            db=db
        )
        
        if payment_result["status"] == "success":
            # 更新订阅期限
            subscription.end_date = subscription.end_date + timedelta(days=subscription.plan.duration_days)
            subscription.last_payment_id = order.id
            order.status = OrderStatus.COMPLETED
            db.commit()
            
            return {
                "message": "Subscription renewed successfully",
                "new_end_date": subscription.end_date,
                "payment_status": payment_result["status"]
            }
        else:
            return {
                "message": "Renewal payment processing",
                "payment_url": payment_result.get("payment_url"),
                "payment_status": payment_result["status"]
            }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Renewal processing failed: {str(e)}"
        )


@router.post("/cancel", response_model=dict)
def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消订阅"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == SubscriptionStatus.ACTIVE
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )

    subscription.status = SubscriptionStatus.CANCELLED
    subscription.auto_renew = False
    db.commit()

    return {
        "message": "Subscription cancelled successfully",
        "end_date": subscription.end_date
    }


@router.post("/toggle-auto-renew", response_model=dict)
def toggle_auto_renew(
    auto_renew: bool,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """切换自动续费状态"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == SubscriptionStatus.ACTIVE
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )

    subscription.auto_renew = auto_renew
    db.commit()

    return {
        "message": f"Auto-renew {'enabled' if auto_renew else 'disabled'} successfully",
        "auto_renew": subscription.auto_renew
    }


@router.get("/history", response_model=List[dict])
def get_subscription_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取订阅历史"""
    subscriptions = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).order_by(Subscription.created_at.desc()).all()

    return [
        {
            "id": sub.id,
            "plan": {
                "id": sub.plan.id,
                "name": sub.plan.name,
                "type": sub.plan.type
            },
            "status": sub.status,
            "start_date": sub.start_date,
            "end_date": sub.end_date,
            "auto_renew": sub.auto_renew,
            "created_at": sub.created_at
        }
        for sub in subscriptions
    ]
