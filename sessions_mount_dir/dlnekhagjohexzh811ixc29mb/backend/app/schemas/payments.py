from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from enum import Enum


class PaymentType(str, Enum):
    MEMBERSHIP = "membership"
    COURSE = "course"
    PERSONAL_TRAINING = "personal_training"
    OTHER = "other"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentBase(BaseModel):
    member_id: int
    amount: float
    payment_date: datetime
    payment_type: PaymentType
    status: PaymentStatus = PaymentStatus.PENDING
    description: Optional[str] = None
    course_id: Optional[int] = None
    coach_id: Optional[int] = None
    transaction_id: Optional[str] = None


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    member_id: Optional[int] = None
    amount: Optional[float] = None
    payment_date: Optional[datetime] = None
    payment_type: Optional[PaymentType] = None
    status: Optional[PaymentStatus] = None
    description: Optional[str] = None
    course_id: Optional[int] = None
    coach_id: Optional[int] = None
    transaction_id: Optional[str] = None


class Payment(PaymentBase):
    id: int

    class Config:
        orm_mode = True