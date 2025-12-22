from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class MemberCardStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    LOST = "lost"


class MemberCardBase(BaseModel):
    member_id: int
    card_number: str
    expiry_date: date
    status: MemberCardStatus


class MemberCardCreate(MemberCardBase):
    pass


class MemberCardUpdate(BaseModel):
    expiry_date: Optional[date] = None
    status: Optional[MemberCardStatus] = None


class MemberCard(MemberCardBase):
    id: int

    class Config:
        orm_mode = True