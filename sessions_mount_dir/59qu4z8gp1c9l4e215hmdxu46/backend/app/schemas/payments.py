from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class PaymentStatus(str, Enum):
    REVERSED = "reversed"
    PROCESSING = "processing"
    CANCELLED = "cancelled"
    PARTIALLY_REFUNDED = "partially_refunded"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class RefundStatus(str, Enum):
    REVERSED = "reversed"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
class PaymentBase(BaseModel):
    original_amount: float = Field(..., description="原始支付金额")
    refund_amount: float = Field(0.0, description="已退款金额")
    refund_reason: Optional[str] = Field(None, description="退款原因")
    refunded_at: Optional[datetime] = Field(None, description="退款时间")
    refund_requested_at: Optional[datetime] = Field(None, description="退款申请时间")
    refund_processed_at: Optional[datetime] = Field(None, description="退款处理时间")
    refund_operator_id: Optional[int] = Field(None, description="退款操作人ID")
    refund_operator_name: Optional[str] = Field(None, description="退款操作人姓名")
    refund_status: Optional[RefundStatus] = Field(None, description="退款状态")
    refund_transaction_id: Optional[str] = Field(None, description="退款交易ID")
    member_id: int = Field(..., description="关联会员ID")
    amount: float = Field(..., description="支付金额")
    payment_method: str = Field(..., description="支付方式")
    transaction_id: Optional[str] = Field(None, description="第三方交易ID")
    status: PaymentStatus = Field(PaymentStatus.PENDING, description="支付状态")
    currency: str = Field("CNY", description="货币类型")
    note: Optional[str] = Field(None, description="备注信息")


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    status: Optional[PaymentStatus] = Field(None, description="支付状态")
    transaction_id: Optional[str] = Field(None, description="第三方交易ID")
    refund_amount: Optional[float] = Field(None, description="已退款金额")
    refund_reason: Optional[str] = Field(None, description="退款原因")
    refunded_at: Optional[datetime] = Field(None, description="退款时间")
    refund_requested_at: Optional[datetime] = Field(None, description="退款申请时间")
    refund_processed_at: Optional[datetime] = Field(None, description="退款处理时间")
    refund_operator_id: Optional[int] = Field(None, description="退款操作人ID")
    refund_operator_name: Optional[str] = Field(None, description="退款操作人姓名")
    refund_status: Optional[RefundStatus] = Field(None, description="退款状态")
    refund_transaction_id: Optional[str] = Field(None, description="退款交易ID")
    currency: Optional[str] = Field(None, description="货币类型")
    note: Optional[str] = Field(None, description="备注信息")


class PaymentInDB(PaymentBase):
class PaymentOut(PaymentInDB):
    member_name: str = Field(..., description="会员姓名")
    member_phone: str = Field(..., description="会员电话")
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class RefundBase(BaseModel):
    payment_id: int = Field(..., description="关联支付记录ID")
    original_payment_id: int = Field(..., description="原始支付记录ID")
    refund_method: str = Field(..., description="退款方式")
    refund_channel: str = Field(..., description="退款渠道")
    refund_fee: float = Field(0.0, description="退款手续费")
    amount: float = Field(..., description="退款金额")
    reason: str = Field(..., description="退款原因")
    status: RefundStatus = Field(RefundStatus.PENDING, description="退款状态")


class RefundCreate(RefundBase):
    pass


class RefundInDB(RefundBase):
class RefundOut(RefundInDB):
    refund_method: str = Field(..., description="退款方式")
    refund_channel: str = Field(..., description="退款渠道")
    refund_fee: float = Field(0.0, description="退款手续费")
    payment_amount: float = Field(..., description="原支付金额")
    member_name: str = Field(..., description="会员姓名")
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class InvoiceBase(BaseModel):
    payment_id: int = Field(..., description="关联支付记录ID")
    invoice_number: str = Field(..., description="发票号码")
    amount: float = Field(..., description="发票金额")
    tax_amount: float = Field(..., description="税额")
    issued_at: datetime = Field(..., description="开票时间")


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceInDB(InvoiceBase):
class InvoiceOut(InvoiceInDB):
    member_name: str = Field(..., description="会员姓名")
    payment_amount: float = Field(..., description="支付金额")
    id: int

    class Config:
        orm_mode = True