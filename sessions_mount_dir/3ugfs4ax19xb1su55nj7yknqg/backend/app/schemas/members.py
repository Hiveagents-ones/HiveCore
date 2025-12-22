from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from enum import Enum


class MembershipStatus(str, Enum):
    active = "active"
    expired = "expired"
    suspended = "suspended"
    pending = "pending"


class MemberBase(BaseModel):
    name: str
    email: EmailStr
    phone: str
    membership_status: MembershipStatus


class MemberCreate(MemberBase):
    pass


class MemberUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    membership_status: Optional[MembershipStatus] = None


class Member(MemberBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True