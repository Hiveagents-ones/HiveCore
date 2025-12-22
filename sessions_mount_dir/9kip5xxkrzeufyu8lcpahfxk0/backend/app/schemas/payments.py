from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class PaymentMethod(str, Enum):

    """支付方式枚举"""
    CASH = "cash"
    WECHAT = "wechat"
    ALIPAY = "alipay"
    BANK_TRANSFER = "bank_transfer"
    OTHER = "other"


class FeeType(str, Enum):
    """费用类型枚举"""
    MEMBERSHIP = "membership"
    COURSE = "course"
    PERSONAL_TRAINING = "personal_training"
    OTHER = "other"


class PaymentStatus(str, Enum):
    """支付状态枚举"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentBase(BaseModel):
    """支付基础模型"""
    amount: float = Field(..., gt=0, description="支付金额")
    method: PaymentMethod = Field(..., description="支付方式")
    fee_type: FeeType = Field(..., description="费用类型")
    transaction_id: Optional[str] = Field(None, max_length=100, description="第三方交易ID")
    payer_id: int = Field(..., description="支付人ID")
    payer_type: str = Field(..., description="支付人类型(member/other)")
    description: Optional[str] = Field(None, max_length=500, description="支付描述")
    related_id: Optional[int] = Field(None, description="关联ID(如会员卡ID、课程ID等)")


class PaymentCreate(PaymentBase):
    """创建支付模型"""
    """创建支付模型"""
    pass


class PaymentUpdate(BaseModel):
    """更新支付模型"""
    """更新支付模型"""
    status: Optional[PaymentStatus] = None
    transaction_id: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class PaymentInDB(PaymentBase):
    """数据库支付模型"""
    """数据库支付模型"""
    id: int
    status: PaymentStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class Payment(PaymentInDB):
    """支付响应模型"""
    pass


class PaymentQuery(BaseModel):
    """支付查询模型"""
    """支付查询模型"""
    payer_id: Optional[int] = None
    payer_type: Optional[str] = None
    status: Optional[PaymentStatus] = None
    method: Optional[PaymentMethod] = None
    fee_type: Optional[FeeType] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: Optional[int] = Field(1, ge=1, description="页码")
    page_size: Optional[int] = Field(10, ge=1, le=100, description="每页数量")
    related_id: Optional[int] = None