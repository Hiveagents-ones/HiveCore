import time
from datetime import datetime
from typing import Dict, Any
from app.db import SessionLocal
from app.models import RenewalRecord
import logging

class PaymentService:
    def __init__(self, db: SessionLocal):
        self.db = db

    async def process_renewal_payment(self, user_id: int, amount: float, payment_method: str) -> Dict[str, Any]:
        order_id = f"renew_{user_id}_{int(time.time())}"
        try:
            gateway_response = await self._call_gateway(payment_method, amount, order_id)
            if gateway_response["status"] != "success":
                raise Exception("Payment failed")
            renewal_record = RenewalRecord(
                user_id=user_id,
                order_id=order_id,
                amount=amount,
                status="completed",
                payment_method=payment_method,
                created_at=datetime.utcnow()
            )
            self.db.add(renewal_record)
            self.db.commit()
            return {
                "order_id": order_id,
                "status": "success",
                "transaction_id": gateway_response["transaction_id"]
            }
        except Exception as e:
            self.db.rollback()
            logging.error(f"Payment processing failed: {str(e)}")
            raise

    async def _call_gateway(self, payment_method: str, amount: float, order_id: str) -> Dict[str, Any]:
        # Simulate payment gateway call
        if payment_method == "wechat":
            return {"status": "success", "transaction_id": f"wx_{order_id}"}
        elif payment_method == "alipay":
            return {"status": "success", "transaction_id": f"ali_{order_id}"}
        else:
            raise ValueError("Unsupported payment method")