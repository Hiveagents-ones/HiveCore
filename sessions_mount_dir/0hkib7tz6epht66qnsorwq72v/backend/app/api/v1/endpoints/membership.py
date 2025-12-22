from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime, timedelta

from ....core.database import get_db
from ....crud.payment import PaymentCRUD
from ....schemas.payment import PaymentOrderCreate, PaymentOrderUpdate, PaymentOrderResponse
from ....models.payment import PaymentStatus
from ....core.payment_gateway import PaymentGateway
from ....gateways.alipay import AlipayGateway
from ....gateways.wechat_pay import WechatPayGateway
from ....gateways.stripe import StripeGateway

router = APIRouter()

# Payment gateway factory
def get_payment_gateway(method: str) -> PaymentGateway:
    if method == "alipay":
        return AlipayGateway()
    elif method == "wechat":
        return WechatPayGateway()
    elif method == "stripe":
        return StripeGateway()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported payment method"
        )

@router.post("/purchase", response_model=PaymentOrderResponse)
def purchase_membership(
    order_data: PaymentOrderCreate,
    db: Session = Depends(get_db)
):
    """Create a new membership purchase order"""
    crud = PaymentCRUD(db)
    
    # Validate payment method
    try:
        gateway = get_payment_gateway(order_data.payment_method)
    except HTTPException as e:
        raise e
    
    # Create payment order
    order = crud.create_payment_order(order_data)
    
    # Initialize payment with gateway
    try:
        payment_result = gateway.create_payment(
            order_id=str(order.id),
            amount=order.amount,
            currency=order.currency,
            description=order.description or "Membership purchase"
        )
        
        # Update order with gateway transaction ID
        crud.update_payment_order(
            order.id,
            PaymentOrderUpdate(gateway_transaction_id=payment_result["transaction_id"])
        )
        
        return PaymentOrderResponse(
            id=order.id,
            user_id=order.user_id,
            membership_id=order.membership_id,
            amount=order.amount,
            currency=order.currency,
            status=order.status,
            payment_method=order.payment_method,
            description=order.description,
            gateway_transaction_id=payment_result["transaction_id"],
            payment_url=payment_result.get("payment_url"),
            qr_code=payment_result.get("qr_code"),
            created_at=order.created_at,
            updated_at=order.updated_at,
            expires_at=order.expires_at
        )
    except Exception as e:
        # If payment initialization fails, mark order as failed
        crud.update_payment_order_status(order.id, PaymentStatus.FAILED)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment initialization failed: {str(e)}"
        )

@router.post("/renew", response_model=PaymentOrderResponse)
def renew_membership(
    order_data: PaymentOrderCreate,
    db: Session = Depends(get_db)
):
    """Create a membership renewal order"""
    crud = PaymentCRUD(db)
    
    # Validate payment method
    try:
        gateway = get_payment_gateway(order_data.payment_method)
    except HTTPException as e:
        raise e
    
    # Create payment order with renewal metadata
    order_data.metadata = {**(order_data.metadata or {}), "type": "renewal"}
    order = crud.create_payment_order(order_data)
    
    # Initialize payment with gateway
    try:
        payment_result = gateway.create_payment(
            order_id=str(order.id),
            amount=order.amount,
            currency=order.currency,
            description=order.description or "Membership renewal"
        )
        
        # Update order with gateway transaction ID
        crud.update_payment_order(
            order.id,
            PaymentOrderUpdate(gateway_transaction_id=payment_result["transaction_id"])
        )
        
        return PaymentOrderResponse(
            id=order.id,
            user_id=order.user_id,
            membership_id=order.membership_id,
            amount=order.amount,
            currency=order.currency,
            status=order.status,
            payment_method=order.payment_method,
            description=order.description,
            gateway_transaction_id=payment_result["transaction_id"],
            payment_url=payment_result.get("payment_url"),
            qr_code=payment_result.get("qr_code"),
            created_at=order.created_at,
            updated_at=order.updated_at,
            expires_at=order.expires_at
        )
    except Exception as e:
        # If payment initialization fails, mark order as failed
        crud.update_payment_order_status(order.id, PaymentStatus.FAILED)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment initialization failed: {str(e)}"
        )

@router.post("/upgrade", response_model=PaymentOrderResponse)
def upgrade_membership(
    order_data: PaymentOrderCreate,
    db: Session = Depends(get_db)
):
    """Create a membership upgrade order"""
    crud = PaymentCRUD(db)
    
    # Validate payment method
    try:
        gateway = get_payment_gateway(order_data.payment_method)
    except HTTPException as e:
        raise e
    
    # Create payment order with upgrade metadata
    order_data.metadata = {**(order_data.metadata or {}), "type": "upgrade"}
    order = crud.create_payment_order(order_data)
    
    # Initialize payment with gateway
    try:
        payment_result = gateway.create_payment(
            order_id=str(order.id),
            amount=order.amount,
            currency=order.currency,
            description=order.description or "Membership upgrade"
        )
        
        # Update order with gateway transaction ID
        crud.update_payment_order(
            order.id,
            PaymentOrderUpdate(gateway_transaction_id=payment_result["transaction_id"])
        )
        
        return PaymentOrderResponse(
            id=order.id,
            user_id=order.user_id,
            membership_id=order.membership_id,
            amount=order.amount,
            currency=order.currency,
            status=order.status,
            payment_method=order.payment_method,
            description=order.description,
            gateway_transaction_id=payment_result["transaction_id"],
            payment_url=payment_result.get("payment_url"),
            qr_code=payment_result.get("qr_code"),
            created_at=order.created_at,
            updated_at=order.updated_at,
            expires_at=order.expires_at
        )
    except Exception as e:
        # If payment initialization fails, mark order as failed
        crud.update_payment_order_status(order.id, PaymentStatus.FAILED)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment initialization failed: {str(e)}"
        )

@router.get("/orders/{user_id}", response_model=List[PaymentOrderResponse])
def get_user_orders(
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all payment orders for a user"""
    crud = PaymentCRUD(db)
    orders = crud.get_payment_orders_by_user(user_id, skip=skip, limit=limit)
    
    return [
        PaymentOrderResponse(
            id=order.id,
            user_id=order.user_id,
            membership_id=order.membership_id,
            amount=order.amount,
            currency=order.currency,
            status=order.status,
            payment_method=order.payment_method,
            description=order.description,
            gateway_transaction_id=order.gateway_transaction_id,
            payment_url=None,
            qr_code=None,
            created_at=order.created_at,
            updated_at=order.updated_at,
            expires_at=order.expires_at
        )
        for order in orders
    ]

@router.get("/order/{order_id}", response_model=PaymentOrderResponse)
def get_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get a specific payment order"""
    crud = PaymentCRUD(db)
    order = crud.get_payment_order(order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return PaymentOrderResponse(
        id=order.id,
        user_id=order.user_id,
        membership_id=order.membership_id,
        amount=order.amount,
        currency=order.currency,
        status=order.status,
        payment_method=order.payment_method,
        description=order.description,
        gateway_transaction_id=order.gateway_transaction_id,
        payment_url=None,
        qr_code=None,
        created_at=order.created_at,
        updated_at=order.updated_at,
        expires_at=order.expires_at
    )

@router.post("/webhook/{payment_method}")
def payment_webhook(
    payment_method: str,
    payload: dict,
    db: Session = Depends(get_db)
):
    """Handle payment webhook notifications"""
    try:
        gateway = get_payment_gateway(payment_method)
    except HTTPException as e:
        raise e
    
    # Verify webhook signature
    if not gateway.verify_webhook(payload):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature"
        )
    
    # Process webhook
    try:
        result = gateway.process_webhook(payload)
        crud = PaymentCRUD(db)
        
        # Update order status based on webhook
        order_id = uuid.UUID(result["order_id"])
        status = result["status"]
        
        crud.update_payment_order_status(order_id, status)
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )
