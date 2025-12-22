from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, EmailStr


class CardStatus(str, Enum):
    active = "active"
    expired = "expired"
    suspended = "suspended"
    canceled = "canceled"


class MemberBase(BaseModel):
    name: str
    phone: str
    email: EmailStr


class MemberCreate(MemberBase):
    card_status: CardStatus = CardStatus.active


class MemberUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    card_status: Optional[CardStatus] = None


class Member(MemberBase):
    id: int
    card_status: CardStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class MemberPayment(BaseModel):
    id: int
    amount: float
    payment_date: datetime
    description: str

    class Config:
        orm_mode = True


class MemberWithPayments(Member):
    payments: List[MemberPayment] = []

    class Config:
        orm_mode = True