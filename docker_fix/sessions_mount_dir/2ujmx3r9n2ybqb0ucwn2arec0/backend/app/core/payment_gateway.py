from enum import Enum
from typing import Dict, Optional, Any
from datetime import datetime
import asyncio
import hashlib
import json
import logging
from abc import ABC, abstractmethod

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..services.membership_service import MembershipService
from ..models.payment import Payment, PaymentStatus
from ..models.membership import Membership
from ..database import get_db
from ..redis_client import redis_client

logger = logging.getLogger(__name__)


class PaymentProvider(Enum):
    WECHAT = "wechat"
    ALIPAY = "alipay"


class PaymentState(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PaymentGateway(ABC):
    @abstractmethod
    async def create_payment(self, order_id: str, amount: float, user_id: int, **kwargs) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def verify_callback(self, callback_data: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    async def query_payment(self, order_id: str) -> Dict[str, Any]:
        pass


class WechatPaymentGateway(PaymentGateway):
    def __init__(self):
        self.app_id = "your_wechat_app_id"
        self.mch_id = "your_mch_id"
        self.api_key = "your_api_key"

    async def create_payment(self, order_id: str, amount: float, user_id: int, **kwargs) -> Dict[str, Any]:
        # Simulate WeChat payment creation
        payment_data = {
            "appid": self.app_id,
            "mch_id": self.mch_id,
            "out_trade_no": order_id,
            "total_fee": int(amount * 100),
            "body": f"Membership renewal for user {user_id}",
            "notify_url": kwargs.get("notify_url", ""),
            "trade_type": "NATIVE"
        }
        
        # Simulate API response
        return {
            "code_url": f"weixin://wxpay/bizpayurl?pr={order_id}",
            "prepay_id": f"prepay_{order_id}",
            "order_id": order_id
        }

    async def verify_callback(self, callback_data: Dict[str, Any]) -> bool:
        # Simulate signature verification
        return callback_data.get("return_code") == "SUCCESS"

    async def query_payment(self, order_id: str) -> Dict[str, Any]:
        # Simulate payment query
        return {
            "trade_state": "SUCCESS",
            "transaction_id": f"tx_{order_id}",
            "order_id": order_id
        }


class AlipayPaymentGateway(PaymentGateway):
    def __init__(self):
        self.app_id = "your_alipay_app_id"
        self.private_key = "your_private_key"
        self.public_key = "your_public_key"

    async def create_payment(self, order_id: str, amount: float, user_id: int, **kwargs) -> Dict[str, Any]:
        # Simulate Alipay payment creation
        payment_data = {
            "app_id": self.app_id,
            "method": "alipay.trade.page.pay",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "notify_url": kwargs.get("notify_url", ""),
            "biz_content": json.dumps({
                "out_trade_no": order_id,
                "product_code": "FAST_INSTANT_TRADE_PAY",
                "total_amount": str(amount),
                "subject": f"Membership renewal for user {user_id}"
            })
        }
        
        # Simulate API response
        return {
            "pay_url": f"https://openapi.alipay.com/gateway.do?order_id={order_id}",
            "order_id": order_id
        }

    async def verify_callback(self, callback_data: Dict[str, Any]) -> bool:
        # Simulate signature verification
        return callback_data.get("trade_status") == "TRADE_SUCCESS"

    async def query_payment(self, order_id: str) -> Dict[str, Any]:
        # Simulate payment query
        return {
            "trade_status": "TRADE_SUCCESS",
            "trade_no": f"alipay_{order_id}",
            "order_id": order_id
        }


class PaymentStateMachine:
    def __init__(self, payment: Payment):
        self.payment = payment
        self.state_transitions = {
            PaymentState.PENDING: [PaymentState.PROCESSING, PaymentState.CANCELLED],
            PaymentState.PROCESSING: [PaymentState.SUCCESS, PaymentState.FAILED],
            PaymentState.SUCCESS: [],
            PaymentState.FAILED: [PaymentState.PENDING],
            PaymentState.CANCELLED: [PaymentState.PENDING]
        }

    def can_transition_to(self, new_state: PaymentState) -> bool:
        current_state = PaymentState(self.payment.status)
        return new_state in self.state_transitions.get(current_state, [])

    def transition_to(self, new_state: PaymentState) -> bool:
        if not self.can_transition_to(new_state):
            logger.error(f"Invalid state transition from {self.payment.status} to {new_state.value}")
            return False
        
        self.payment.status = new_state.value
        self.payment.updated_at = datetime.utcnow()
        return True


class PaymentProcessor:
    def __init__(self):
        self.gateways = {
            PaymentProvider.WECHAT: WechatPaymentGateway(),
            PaymentProvider.ALIPAY: AlipayPaymentGateway()
        }
        self.membership_service = MembershipService()

    async def create_payment(
        self,
        db: Session,
        user_id: int,
        provider: PaymentProvider,
        amount: float,
        membership_plan_id: int,
        **kwargs
    ) -> Dict[str, Any]:
        # Generate unique order ID
        order_id = f"{provider.value}_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create payment record
        payment = Payment(
            order_id=order_id,
            user_id=user_id,
            provider=provider.value,
            amount=amount,
            status=PaymentState.PENDING.value,
            membership_plan_id=membership_plan_id
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        # Initialize state machine
        state_machine = PaymentStateMachine(payment)
        
        # Create payment with provider
        gateway = self.gateways[provider]
        payment_data = await gateway.create_payment(
            order_id=order_id,
            amount=amount,
            user_id=user_id,
            **kwargs
        )

        # Update payment state
        state_machine.transition_to(PaymentState.PROCESSING)
        db.commit()

        # Cache payment info for idempotency
        await self._cache_payment_info(payment)

        return {
            "payment_id": payment.id,
            "order_id": order_id,
            "payment_url": payment_data.get("pay_url") or payment_data.get("code_url"),
            "status": payment.status
        }

    async def handle_callback(
        self,
        db: Session,
        provider: PaymentProvider,
        callback_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Verify callback
        gateway = self.gateways[provider]
        if not await gateway.verify_callback(callback_data):
            raise HTTPException(status_code=400, detail="Invalid callback signature")

        # Get order ID from callback
        order_id = callback_data.get("out_trade_no") or callback_data.get("order_id")
        if not order_id:
            raise HTTPException(status_code=400, detail="Missing order ID")

        # Check idempotency
        cache_key = f"payment_callback:{order_id}"
        if await redis_client.exists(cache_key):
            logger.info(f"Duplicate callback for order {order_id}")
            return {"status": "duplicate", "order_id": order_id}

        # Get payment record
        payment = db.query(Payment).filter(Payment.order_id == order_id).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        # Initialize state machine
        state_machine = PaymentStateMachine(payment)

        # Process payment result
        if callback_data.get("return_code") == "SUCCESS" or callback_data.get("trade_status") == "TRADE_SUCCESS":
            if state_machine.transition_to(PaymentState.SUCCESS):
                # Update membership
                await self.membership_service.renew_membership(
                    db=db,
                    user_id=payment.user_id,
                    plan_id=payment.membership_plan_id
                )
                
                # Cache successful callback
                await redis_client.setex(cache_key, 3600, "success")
                
                return {"status": "success", "order_id": order_id}
        else:
            state_machine.transition_to(PaymentState.FAILED)
            await redis_client.setex(cache_key, 3600, "failed")
            return {"status": "failed", "order_id": order_id}

        db.commit()
        return {"status": "processed", "order_id": order_id}

    async def query_payment_status(self, db: Session, order_id: str) -> Dict[str, Any]:
        # Check cache first
        cache_key = f"payment_status:{order_id}"
        cached_status = await redis_client.get(cache_key)
        if cached_status:
            return {"order_id": order_id, "status": cached_status.decode()}

        # Get payment from database
        payment = db.query(Payment).filter(Payment.order_id == order_id).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        # If payment is still processing, query provider
        if payment.status == PaymentState.PROCESSING.value:
            provider = PaymentProvider(payment.provider)
            gateway = self.gateways[provider]
            provider_status = await gateway.query_payment(order_id)
            
            # Update payment status based on provider response
            state_machine = PaymentStateMachine(payment)
            if provider_status.get("trade_state") == "SUCCESS" or provider_status.get("trade_status") == "TRADE_SUCCESS":
                state_machine.transition_to(PaymentState.SUCCESS)
                await self.membership_service.renew_membership(
                    db=db,
                    user_id=payment.user_id,
                    plan_id=payment.membership_plan_id
                )
            elif provider_status.get("trade_state") == "CLOSED" or provider_status.get("trade_status") == "TRADE_CLOSED":
                state_machine.transition_to(PaymentState.CANCELLED)
            
            db.commit()

        # Cache status
        await redis_client.setex(cache_key, 300, payment.status)

        return {
            "order_id": order_id,
            "status": payment.status,
            "amount": payment.amount,
            "provider": payment.provider,
            "created_at": payment.created_at.isoformat()
        }

    async def _cache_payment_info(self, payment: Payment):
        cache_key = f"payment_info:{payment.order_id}"
        payment_info = {
            "payment_id": payment.id,
            "user_id": payment.user_id,
            "amount": payment.amount,
            "status": payment.status,
            "provider": payment.provider
        }
        await redis_client.setex(cache_key, 3600, json.dumps(payment_info))

    async def cancel_payment(self, db: Session, order_id: str) -> Dict[str, Any]:
        payment = db.query(Payment).filter(Payment.order_id == order_id).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        state_machine = PaymentStateMachine(payment)
        if state_machine.transition_to(PaymentState.CANCELLED):
            db.commit()
            await redis_client.delete(f"payment_info:{order_id}")
            return {"status": "cancelled", "order_id": order_id}
        
        raise HTTPException(status_code=400, detail="Cannot cancel payment in current state")


# Global payment processor instance
payment_processor = PaymentProcessor()