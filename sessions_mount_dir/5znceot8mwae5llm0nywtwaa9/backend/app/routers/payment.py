from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from app.database import get_db
from app.models import User, Membership, Order
from app.schemas import PaymentCreate, PaymentResponse, PaymentCallback
from app.services.payment_gateway import (
    PaymentGateway,
    WechatPaymentGateway,
    AlipayPaymentGateway,
    PaymentMethod,
    PaymentStatus,
    PaymentResult
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payment", tags=["payment"])

# Initialize payment gateways
payment_gateways: Dict[PaymentMethod, PaymentGateway] = {
    PaymentMethod.WECHAT: WechatPaymentGateway(),
    PaymentMethod.ALIPAY: AlipayPaymentGateway(),
}

@router.post("/create", response_model=PaymentResponse)
async def create_payment(
    payment_data: PaymentCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new payment order
    """
    try:
        # Verify user exists
        user = db.query(User).filter(User.id == payment_data.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Verify membership exists
        membership = db.query(Membership).filter(
            Membership.id == payment_data.membership_id
        ).first()
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Membership plan not found"
            )

        # Create order record
        order = Order(
            user_id=payment_data.user_id,
            membership_id=payment_data.membership_id,
            amount=membership.price,
            payment_method=payment_data.payment_method.value,
            status=PaymentStatus.PENDING.value
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        # Process payment through gateway
        gateway = payment_gateways.get(payment_data.payment_method)
        if not gateway:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported payment method"
            )

        result = gateway.create_payment(
            amount=membership.price,
            order_id=str(order.id),
            user_id=payment_data.user_id,
            payment_method=payment_data.payment_method,
            notify_url=f"/api/payment/callback/{payment_data.payment_method.value}"
        )

        if result.status != PaymentStatus.PENDING:
            order.status = result.status.value
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )

        # Update order with transaction ID
        order.transaction_id = result.transaction_id
        db.commit()

        return PaymentResponse(
            order_id=order.id,
            transaction_id=result.transaction_id,
            payment_method=payment_data.payment_method.value,
            amount=membership.price,
            status=result.status.value,
            payment_data=result.data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Payment creation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/callback/{payment_method}")
async def payment_callback(
    payment_method: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle payment callback from payment gateways
    """
    try:
        # Parse payment method
        try:
            method = PaymentMethod(payment_method)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment method"
            )

        # Get payment gateway
        gateway = payment_gateways.get(method)
        if not gateway:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported payment method"
            )

        # Get callback data
        if method == PaymentMethod.WECHAT:
            callback_data = await request.form()
            callback_data = dict(callback_data)
        else:
            callback_data = await request.json()

        # Verify payment
        result = gateway.verify_payment(callback_data)

        # Find order
        order = db.query(Order).filter(
            Order.transaction_id == result.transaction_id
        ).first()
        if not order:
            logger.error(f"Order not found for transaction: {result.transaction_id}")
            return {"status": "fail", "message": "Order not found"}

        # Update order status
        order.status = result.status.value
        if result.status == PaymentStatus.SUCCESS:
            # Update user membership
            user = db.query(User).filter(User.id == order.user_id).first()
            membership = db.query(Membership).filter(
                Membership.id == order.membership_id
            ).first()
            
            if user and membership:
                # Extend membership
                if user.membership_end:
                    from datetime import timedelta
                    user.membership_end += timedelta(days=membership.duration_days)
                else:
                    from datetime import datetime, timedelta
                    user.membership_end = datetime.utcnow() + timedelta(days=membership.duration_days)
                user.membership_type = membership.type

        db.commit()

        return {"status": "success", "message": "Callback processed"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Payment callback failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/confirm-offline/{order_id}")
async def confirm_offline_payment(
    order_id: int,
    db: Session = Depends(get_db)
):
    """
    Confirm offline payment (admin only)
    """
    try:
        # Find order
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )

        if order.payment_method != PaymentMethod.OFFLINE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not an offline payment order"
            )

        if order.status != PaymentStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order already processed"
            )

        # Update order status
        order.status = PaymentStatus.SUCCESS.value
        order.transaction_id = f"offline_{order.id}_{order.user_id}"

        # Update user membership
        user = db.query(User).filter(User.id == order.user_id).first()
        membership = db.query(Membership).filter(
            Membership.id == order.membership_id
        ).first()
        
        if user and membership:
            # Extend membership
            if user.membership_end:
                from datetime import timedelta
                user.membership_end += timedelta(days=membership.duration_days)
            else:
                from datetime import datetime, timedelta
                user.membership_end = datetime.utcnow() + timedelta(days=membership.duration_days)
            user.membership_type = membership.type

        db.commit()

        return {"status": "success", "message": "Offline payment confirmed"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Offline payment confirmation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
