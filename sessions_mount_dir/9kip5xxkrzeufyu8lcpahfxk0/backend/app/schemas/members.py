from datetime import date
from typing import Optional
from pydantic import BaseModel, EmailStr
from pydantic import SecretStr


class MemberBase(BaseModel):
    name: str
    phone: SecretStr
    email: EmailStr
    join_date: date


class MemberCreate(MemberBase):
    pass


class MemberUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[SecretStr] = None
    email: Optional[EmailStr] = None


class Member(MemberBase):
    id: int

    class Config:
        orm_mode = True


class MemberCardBase(BaseModel):
    card_number: SecretStr
    expiry_date: date
    status: str


class MemberCardCreate(MemberCardBase):
    member_id: int


class MemberCardUpdate(BaseModel):
    card_number: Optional[SecretStr] = None
    expiry_date: Optional[date] = None
    status: Optional[str] = None


class MemberCard(MemberCardBase):
    id: int
    member_id: int

    class Config:
        orm_mode = True