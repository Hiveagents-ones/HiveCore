from fastapi import APIRouter, HTTPException, Request
from app.services.payment_service import PaymentService
from app.db import get_db, SessionLocal
from pydantic import BaseModel
import logging

router = APIRouter()

class PaymentRequest(BaseModel):
    user_id: int
    amount: float
    payment_method: str

@router.post("/payments")
async def initiate_renewal_payment(
    payment_data: PaymentRequest,
    request: Request,
    db: SessionLocal = Depends(get_db)
):
    # Validate payment method
    if payment_data.payment_method not in ["wechat", "alipay"]:
        raise HTTPException(
            status_code=400,
            detail="Unsupported payment method. Use 'wechat' or 'alipay'."
        )

    # Audit logging
    logging.info(
        f"Initiating renewal payment for user {payment_data.user_id} (amount: {payment_data.amount}, method: {payment_data.payment_method})"
    )

    payment_service = PaymentService(db)
    try:
        return await payment_service.process_renewal_payment(
            user_id=payment_data.user_id,
            amount=payment_data.amount,
            payment_method=payment_data.payment_method
        )
    except Exception as e:
        logging.error(f"Payment processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Payment processing failed")