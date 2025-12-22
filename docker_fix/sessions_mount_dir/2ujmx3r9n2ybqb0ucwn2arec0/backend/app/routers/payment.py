from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any
import uuid
import logging
from datetime import datetime

from ..database import get_db
from ..models.payment import Payment, PaymentStatus
from ..models.membership import Membership
from ..services.membership_service import MembershipService
from ..core.payment_gateway import PaymentProvider, PaymentGateway, WechatPaymentGateway, AlipayPaymentGateway
from ..redis_client import redis_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payment", tags=["payment"])

# Payment gateway instances
payment_gateways: Dict[PaymentProvider, PaymentGateway] = {
    PaymentProvider.WECHAT: WechatPaymentGateway(),
    PaymentProvider.ALIPAY: AlipayPaymentGateway()
}


@router.post("/create")
async def create_payment(
    request: Request,
    background_tasks: BackgroundTasks,
    provider: PaymentProvider,
    amount: float,
    user_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create a new payment with idempotency check
    """
    # Generate unique order ID
    order_id = str(uuid.uuid4())
    
    # Check for idempotency using Redis
    idempotency_key = f"payment:{user_id}:{amount}:{provider.value}"
    existing_payment = await redis_client.get(idempotency_key)
    
    if existing_payment:
        logger.info(f"Idempotency key hit for user {user_id}")
        return {
            "order_id": existing_payment.decode(),
            "status": "pending",
            "message": "Payment already created"
        }
    
    # Store idempotency key
    await redis_client.setex(idempotency_key, 3600, order_id)  # 1 hour expiry
    
    # Create payment record
    payment = Payment(
        order_id=order_id,
        user_id=user_id,
        amount=amount,
        provider=provider.value,
        status=PaymentStatus.PENDING,
        created_at=datetime.utcnow()
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    # Get payment gateway
    gateway = payment_gateways.get(provider)
    if not gateway:
        raise HTTPException(status_code=400, detail="Unsupported payment provider")
    
    # Create payment with provider
    try:
        payment_data = await gateway.create_payment(
            order_id=order_id,
            amount=amount,
            user_id=user_id,
            notify_url=f"{request.url.scheme}://{request.url.netloc}/payment/callback/{provider.value}"
        )
        
        # Update payment with provider data
        payment.provider_payment_id = payment_data.get("prepay_id") or payment_data.get("order_id")
        payment.status = PaymentStatus.PROCESSING
        db.commit()
        
        return {
            "order_id": order_id,
            "payment_url": payment_data.get("code_url") or payment_data.get("payment_url"),
            "status": "processing"
        }
    except Exception as e:
        logger.error(f"Payment creation failed: {str(e)}")
        payment.status = PaymentStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail="Payment creation failed")


@router.post("/callback/{provider}")
async def payment_callback(
    provider: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Handle payment callback from provider
    """
    try:
        provider_enum = PaymentProvider(provider)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payment provider")
    
    gateway = payment_gateways.get(provider_enum)
    if not gateway:
        raise HTTPException(status_code=400, detail="Unsupported payment provider")
    
    # Get callback data
    callback_data = await request.json()
    
    # Verify callback
    if not await gateway.verify_callback(callback_data):
        raise HTTPException(status_code=400, detail="Invalid callback signature")
    
    # Get order ID from callback
    order_id = callback_data.get("out_trade_no") or callback_data.get("order_id")
    if not order_id:
        raise HTTPException(status_code=400, detail="Missing order ID")
    
    # Find payment record
    payment = db.query(Payment).filter(Payment.order_id == order_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Check if already processed
    if payment.status == PaymentStatus.SUCCESS:
        return {"status": "success", "message": "Payment already processed"}
    
    # Update payment status
    payment.status = PaymentStatus.SUCCESS
    payment.completed_at = datetime.utcnow()
    payment.transaction_id = callback_data.get("transaction_id")
    db.commit()
    
    # Process membership renewal in background
    background_tasks.add_task(process_membership_renewal, payment.user_id, payment.amount, db)
    
    return {"status": "success", "message": "Payment processed successfully"}


@router.get("/status/{order_id}")
async def get_payment_status(
    order_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get payment status with order status query
    """
    # Check cache first
    cache_key = f"payment_status:{order_id}"
    cached_status = await redis_client.get(cache_key)
    
    if cached_status:
        return {"order_id": order_id, "status": cached_status.decode()}
    
    # Get payment from database
    payment = db.query(Payment).filter(Payment.order_id == order_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # If payment is still pending, query provider
    if payment.status == PaymentStatus.PENDING or payment.status == PaymentStatus.PROCESSING:
        try:
            provider_enum = PaymentProvider(payment.provider)
            gateway = payment_gateways.get(provider_enum)
            if gateway:
                provider_status = await gateway.query_payment(order_id)
                if provider_status.get("trade_state") == "SUCCESS":
                    payment.status = PaymentStatus.SUCCESS
                    payment.completed_at = datetime.utcnow()
                    payment.transaction_id = provider_status.get("transaction_id")
                    db.commit()
        except Exception as e:
            logger.error(f"Failed to query payment status: {str(e)}")
    
    # Cache status for 5 minutes
    await redis_client.setex(cache_key, 300, payment.status.value)
    
    return {
        "order_id": order_id,
        "status": payment.status.value,
        "created_at": payment.created_at.isoformat(),
        "completed_at": payment.completed_at.isoformat() if payment.completed_at else None,
        "amount": payment.amount,
        "provider": payment.provider
    }


async def process_membership_renewal(user_id: int, amount: float, db: Session):
    """
    Process membership renewal after successful payment
    """
    try:
        membership_service = MembershipService(db)
        await membership_service.renew_membership(user_id, amount)
        logger.info(f"Membership renewed for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to renew membership for user {user_id}: {str(e)}")
        # In a real system, you might want to implement a retry mechanism
        # or notify administrators about the failure
