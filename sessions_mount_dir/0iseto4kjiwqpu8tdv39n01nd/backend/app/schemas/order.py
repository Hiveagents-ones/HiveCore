from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from ..models.order import OrderStatus, PaymentMethod


class OrderBase(BaseModel):
    membership_plan_id: UUID
    payment_method: PaymentMethod
    amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)
    expires_at: Optional[datetime] = None
    is_renewal: bool = False


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    expires_at: Optional[datetime] = None


class OrderResponse(OrderBase):
    id: UUID
    user_id: UUID
    status: OrderStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransactionBase(BaseModel):
    transaction_id: str = Field(..., max_length=100)
    payment_method: PaymentMethod
    amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)
    status: str = Field(..., max_length=50)
    gateway_response: Optional[str] = None


class TransactionCreate(TransactionBase):
    order_id: UUID


class TransactionUpdate(BaseModel):
    status: Optional[str] = None
    gateway_response: Optional[str] = None


class TransactionResponse(TransactionBase):
    id: UUID
    order_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderWithTransactions(OrderResponse):
    transactions: List[TransactionResponse] = []


class PaymentRequest(BaseModel):
    order_id: UUID
    payment_method: PaymentMethod
    return_url: Optional[str] = None
    cancel_url: Optional[str] = None


class PaymentResponse(BaseModel):
    payment_url: Optional[str] = None
    transaction_id: str
    status: str
    message: Optional[str] = None
