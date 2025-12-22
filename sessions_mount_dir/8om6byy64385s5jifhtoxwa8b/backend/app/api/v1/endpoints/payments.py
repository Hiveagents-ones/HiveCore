from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from typing import List
from uuid import UUID
from sqlalchemy.orm import Session

from ....core.database import get_db
from ....crud.payment import PaymentCRUD
from ....schemas.payment import (
    PaymentOrderCreate,
    PaymentOrderResponse,
    PaymentOrderDetail,
    PaymentOrderUpdate,
    PaymentTransactionCreate,
    PaymentTransactionResponse,
    RefundCreate,
    RefundResponse,
    RefundUpdate,
)
from ....core.payment_gateway import PaymentGateway, PaymentStatus
from ....gateways.alipay import AlipayGateway
from ....gateways.wechat_pay import WechatPayGateway
from ....gateways.stripe import StripeGateway
from ....models.payment import PaymentMethod

from ....tasks.payment_tasks import process_payment_webhook

router = APIRouter()


def get_payment_gateway(method: PaymentMethod) -> PaymentGateway:
    """Factory function to get the appropriate payment gateway"""
    if method == PaymentMethod.ALIPAY:
        # Mock config - replace with actual config
        return AlipayGateway({"app_id": "test", "private_key": "test"})
    elif method == PaymentMethod.WECHAT:
        # Mock config - replace with actual config
        return WechatPayGateway({"app_id": "test", "mch_id": "test"})
    elif method == PaymentMethod.STRIPE:
        # Mock config - replace with actual config
        return StripeGateway({
            "secret_key": "sk_test_...",
            "publishable_key": "pk_test_...",
            "webhook_secret": "whsec_..."
        })
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported payment method"
        )


@router.post("/orders", response_model=PaymentOrderResponse)
def create_payment_order(
    order: PaymentOrderCreate,
    db: Session = Depends(get_db)
):
    """Create a new payment order"""
    crud = PaymentCRUD(db)
    db_order = crud.create_payment_order(order)
    return db_order


@router.get("/orders/{order_id}", response_model=PaymentOrderDetail)
def get_payment_order(
    order_id: UUID,
    db: Session = Depends(get_db)
):
    """Get payment order details"""
    crud = PaymentCRUD(db)
    db_order = crud.get_payment_order(order_id)
    if not db_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment order not found"
        )
    return db_order


@router.get("/orders/user/{user_id}", response_model=List[PaymentOrderResponse])
def get_user_payment_orders(
    user_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all payment orders for a user"""
    crud = PaymentCRUD(db)
    orders = crud.get_payment_orders_by_user(user_id, skip=skip, limit=limit)
    return orders


@router.post("/orders/{order_id}/pay")
def initiate_payment(
    order_id: UUID,
    db: Session = Depends(get_db)
):
    """Initiate payment for an order"""
    crud = PaymentCRUD(db)
    db_order = crud.get_payment_order(order_id)
    if not db_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment order not found"
        )
    
    if db_order.status != PaymentStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is not in a payable state"
        )
    
    gateway = get_payment_gateway(db_order.payment_method)
    
    try:
        # Create payment with gateway
        payment_result = gateway.create_payment(
            amount=float(db_order.amount),
            currency=db_order.currency,
            description=db_order.description or "Payment for membership",
            metadata={"order_id": str(order_id)}
        )
        
        # Create transaction record
        transaction_data = PaymentTransactionCreate(
            payment_order_id=order_id,
            gateway_transaction_id=payment_result["payment_id"],
            gateway=gateway.__class__.__name__,
            amount=db_order.amount,
            currency=db_order.currency,
            status=PaymentStatus.PENDING,
            gateway_response=str(payment_result)
        )
        crud.create_payment_transaction(transaction_data)
        
        # Update order with transaction ID
        crud.update_payment_order(order_id, PaymentOrderUpdate(
            transaction_id=payment_result["payment_id"]
        ))
        
        return {
            "payment_id": payment_result["payment_id"],
            "client_secret": payment_result.get("client_secret"),
            "status": payment_result["status"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate payment: {str(e)}"
        )


@router.post("/webhooks/{gateway}")
def handle_webhook(
    gateway: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle payment gateway webhooks"""
    crud = PaymentCRUD(db)
    
    try:
        payload = await request.json()
        
        # Get appropriate gateway
        if gateway.lower() == "stripe":
            payment_gateway = get_payment_gateway(PaymentMethod.STRIPE)
        elif gateway.lower() == "alipay":
            payment_gateway = get_payment_gateway(PaymentMethod.ALIPAY)
        elif gateway.lower() == "wechat":
            payment_gateway = get_payment_gateway(PaymentMethod.WECHAT)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported gateway"
            )
        
        # Process webhook
        webhook_result = payment_gateway.handle_webhook(payload)
        
        # Update payment status based on webhook
        order_id = UUID(webhook_result.get("order_id"))
        payment_status = PaymentStatus(webhook_result.get("status"))
        
        # Update order status
        crud.update_payment_order_status(order_id, payment_status)
        
        # Update transaction status
        transaction = crud.get_latest_transaction_for_order(order_id)
        if transaction:
            crud.update_payment_transaction(transaction.id, {
                "status": payment_status,
                "gateway_response": str(webhook_result)
            })
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}"
        )


@router.post("/orders/{order_id}/refund", response_model=RefundResponse)
def refund_payment(
    order_id: UUID,
    refund_data: RefundCreate,
    db: Session = Depends(get_db)
):
    """Process a refund for a payment order"""
    crud = PaymentCRUD(db)
    db_order = crud.get_payment_order(order_id)
    if not db_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment order not found"
        )
    
    if db_order.status != PaymentStatus.SUCCESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only successful payments can be refunded"
        )
    
    gateway = get_payment_gateway(db_order.payment_method)
    
    try:
        # Process refund with gateway
        refund_result = gateway.refund_payment(
            payment_id=db_order.transaction_id,
            amount=float(refund_data.amount)
        )
        
        # Create refund record
        refund_data.gateway_refund_id = refund_result["refund_id"]
        refund_data.gateway_response = str(refund_result)
        refund_data.status = PaymentStatus.REFUNDED
        
        db_refund = crud.create_refund(refund_data)
        
        # Update order status if fully refunded
        if refund_data.amount >= db_order.amount:
            crud.update_payment_order_status(order_id, PaymentStatus.REFUNDED)
        
        return db_refund
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process refund: {str(e)}"
        )


@router.get("/transactions/{transaction_id}", response_model=PaymentTransactionResponse)
def get_payment_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db)
):
    """Get payment transaction details"""
    crud = PaymentCRUD(db)
    transaction = crud.get_payment_transaction(transaction_id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    return transaction


@router.get("/refunds/{refund_id}", response_model=RefundResponse)
def get_refund(


@router.post("/orders/{order_id}/cancel")
@router.post("/orders/{order_id}/cancel")
def cancel_payment_order(
    order_id: UUID,
    db: Session = Depends(get_db)
):
    """Cancel a pending payment order"""
    crud = PaymentCRUD(db)
    db_order = crud.get_payment_order(order_id)
    if not db_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment order not found"
        )

    if db_order.status != PaymentStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending orders can be cancelled"
        )

    # Update order status to cancelled
    crud.update_payment_order_status(order_id, PaymentStatus.CANCELLED)

    return {"status": "cancelled", "order_id": order_id}
def get_refund(
    refund_id: UUID,
    db: Session = Depends(get_db)
):
    """Get refund details"""
    crud = PaymentCRUD(db)
    refund = crud.get_refund(refund_id)
    if not refund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found"
        )
    return refund
