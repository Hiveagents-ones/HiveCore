from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, validator

from app.models.member import MemberLevel, HealthStatus


class MemberBase(BaseModel):
    name: str
    phone: str
    email: Optional[EmailStr] = None
    member_level: MemberLevel
    join_date: date
    expiry_date: date
    health_status: Optional[HealthStatus] = HealthStatus.GOOD
    health_notes: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    is_active: bool = True

    @validator('expiry_date')
    def expiry_date_must_be_after_join_date(cls, v, values):
        if 'join_date' in values and v <= values['join_date']:
            raise ValueError('expiry_date must be after join_date')
        return v


class MemberCreate(MemberBase):
    pass


class MemberUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    member_level: Optional[MemberLevel] = None
    join_date: Optional[date] = None
    expiry_date: Optional[date] = None
    health_status: Optional[HealthStatus] = None
    health_notes: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    is_active: Optional[bool] = None

    @validator('expiry_date')
    def expiry_date_must_be_after_join_date(cls, v, values):
        if v is not None and 'join_date' in values and values['join_date'] is not None and v <= values['join_date']:
            raise ValueError('expiry_date must be after join_date')
        return v


class MemberInDB(MemberBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class Member(MemberInDB):
    is_membership_valid: bool

    class Config:
        orm_mode = True
        use_enum_values = True


class MemberList(BaseModel):
    members: list[Member]
    total: int
    page: int
    per_page: int
    pages: int
