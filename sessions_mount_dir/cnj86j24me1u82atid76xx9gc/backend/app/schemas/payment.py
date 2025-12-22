from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field
from decimal import Decimal

from ..models.payment import PaymentStatus, PaymentMethod


class PaymentMethodConfig(BaseModel):
    """支付方式配置模型"""
    method: PaymentMethod
    is_enabled: bool = True
    min_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    max_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    fee_rate: Optional[Decimal] = Field(None, ge=0, decimal_places=4)
    fixed_fee: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    description: Optional[str] = None


class MembershipPlanBase(BaseModel):
    """会员计划基础模型"""
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    price: Decimal = Field(..., ge=0, decimal_places=2)
    currency: str = Field(default="USD", max_length=3)
    duration_months: int = Field(..., gt=0)
    features: Optional[List[str]] = None
    is_active: bool = True
    upgrade_from: Optional[List[UUID]] = None


class MembershipPlanCreate(MembershipPlanBase):
    pass


class MembershipPlanUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    duration_months: Optional[int] = Field(None, gt=0)
    features: Optional[List[str]] = None
    is_active: Optional[bool] = None
    upgrade_from: Optional[List[UUID]] = None


class MembershipPlanResponse(MembershipPlanBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionBase(BaseModel):
    """订阅基础模型"""
    user_id: UUID
    membership_plan_id: UUID
    start_date: datetime
    end_date: datetime
    auto_renew: bool = True
    status: PaymentStatus = PaymentStatus.ACTIVE


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionUpdate(BaseModel):
    end_date: Optional[datetime] = None
    auto_renew: Optional[bool] = None
    status: Optional[PaymentStatus] = None


class SubscriptionResponse(SubscriptionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    membership_plan: MembershipPlanResponse

    class Config:
        from_attributes = True


class PaymentSummary(BaseModel):
    """支付汇总统计模型"""
    total_orders: int
    total_amount: Decimal
    successful_orders: int
    successful_amount: Decimal
    refunded_orders: int
    refunded_amount: Decimal
    pending_orders: int
    pending_amount: Decimal
    period_start: datetime
    period_end: datetime


class PaymentAnalytics(BaseModel):
    """支付分析模型"""
    daily_revenue: List[dict]
    payment_methods_distribution: List[dict]
    membership_plans_distribution: List[dict]
    churn_rate: Optional[Decimal] = Field(None, ge=0, decimal_places=4)
    average_revenue_per_user: Optional[Decimal] = Field(None, ge=0, decimal_places=2)



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
