from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime

from .... import models, schemas
from ....crud import get_membership_plan
from ....services.payment_service import PaymentService
from ....core.deps import get_db, get_current_user

router = APIRouter()


@router.post("/create-payment", response_model=schemas.PaymentOrder)
def create_payment(
    plan_id: int,
    payment_method: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    创建支付订单
    """
    # 验证会员套餐是否存在
    plan = get_membership_plan(db, plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership plan not found"
        )
    
    # 创建支付订单
    payment_service = PaymentService(db)
    try:
        payment_order = payment_service.create_payment_order(
            user_id=current_user.id,
            plan_id=plan_id,
            payment_method=payment_method
        )
        return payment_order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/payment-callback")
def payment_callback(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    支付回调处理
    """
    # 获取回调数据
    callback_data: Dict[str, Any] = await request.json()
    
    # 验证必要字段
    required_fields = ["order_id", "transaction_id", "status"]
    for field in required_fields:
        if field not in callback_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}"
            )
    
    # 处理支付结果
    payment_service = PaymentService(db)
    try:
        success = payment_service.process_payment_result(
            order_id=callback_data["order_id"],
            transaction_id=callback_data["transaction_id"],
            status=callback_data["status"]
        )
        
        if success:
            return {"status": "success", "message": "Payment processed successfully"}
        else:
            return {"status": "failed", "message": "Payment processing failed"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/payment-status/{order_id}", response_model=schemas.PaymentOrder)
def get_payment_status(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    查询支付状态
    """
    payment_order = db.query(models.PaymentOrder).filter(
        models.PaymentOrder.order_id == order_id,
        models.PaymentOrder.user_id == current_user.id
    ).first()
    
    if not payment_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment order not found"
        )
    
    return payment_order
