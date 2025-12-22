from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field
from decimal import Decimal

from ..models.payment import PaymentStatus, PaymentMethod


class PaymentOrderBase(BaseModel):
    user_id: UUID
    membership_id: UUID
    amount: Decimal = Field(..., ge=0, decimal_places=2)
    currency: str = Field(default="USD", max_length=3)
    payment_method: PaymentMethod
    description: Optional[str] = None
    metadata: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_recurring: bool = False
    next_billing_date: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None


class PaymentOrderCreate(PaymentOrderBase):
    pass


class PaymentOrderUpdate(BaseModel):
    status: Optional[PaymentStatus] = None
    transaction_id: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[str] = None
    expires_at: Optional[datetime] = None


class PaymentOrderResponse(PaymentOrderBase):
    id: UUID
    status: PaymentStatus
    transaction_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentTransactionBase(BaseModel):
    payment_order_id: UUID
    gateway_transaction_id: str
    gateway: str = Field(..., max_length=50)
    amount: Decimal = Field(..., ge=0, decimal_places=2)
    currency: str = Field(default="USD", max_length=3)
    status: PaymentStatus
    gateway_response: Optional[str] = None
    refund_reason_code: Optional[str] = None
    partial_refund_available: bool = True


class PaymentTransactionCreate(PaymentTransactionBase):
    pass


class PaymentTransactionUpdate(BaseModel):
    status: Optional[PaymentStatus] = None
    gateway_response: Optional[str] = None
    processed_at: Optional[datetime] = None
    refund_reason_code: Optional[str] = None
    partial_refund_available: Optional[bool] = None


class PaymentTransactionResponse(PaymentTransactionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True


class RefundBase(BaseModel):
    payment_order_id: UUID
    amount: Decimal = Field(..., ge=0, decimal_places=2)
    currency: str = Field(default="USD", max_length=3)
    reason: Optional[str] = None
    status: PaymentStatus = PaymentStatus.PENDING
    gateway_refund_id: Optional[str] = None
    gateway_response: Optional[str] = None


class RefundCreate(RefundBase):
    pass


class RefundUpdate(BaseModel):
    status: Optional[PaymentStatus] = None
    gateway_refund_id: Optional[str] = None
    gateway_response: Optional[str] = None
    processed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None


class RefundResponse(RefundBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime]
    failure_reason: Optional[str]

    class Config:
        from_attributes = True


class PaymentOrderDetail(PaymentOrderResponse):
    transactions: List[PaymentTransactionResponse] = []
    refunds: List[RefundResponse] = []

    class Config:
        from_attributes = True
