from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class MemberBase(BaseModel):
    name: str
    phone: str
    email: str
    card_status: str


class MemberCreate(MemberBase):
    pass


class MemberUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    card_status: Optional[str] = None


class Member(MemberBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True