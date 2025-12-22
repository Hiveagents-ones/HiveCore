from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
import re

class MemberBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="会员姓名")
    phone: str = Field(..., min_length=10, max_length=20, description="手机号码")
    email: Optional[str] = Field(None, max_length=100, description="电子邮箱")
    member_card_number: str = Field(..., min_length=1, max_length=50, description="会员卡号")
    member_level: str = Field(default="basic", regex="^(basic|silver|gold|platinum)$", description="会员等级")
    remaining_sessions: int = Field(default=0, ge=0, description="剩余课时")
    expiry_date: Optional[datetime] = Field(None, description="有效期")
    is_active: bool = Field(default=True, description="是否激活")

    @validator('phone')
    def validate_phone(cls, v):
        if not re.match(r'^\+?[1-9]\d{1,14}$', v):
            raise ValueError('Invalid phone number format')
        return v

    @validator('email')
    def validate_email(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v

class MemberCreate(MemberBase):
    pass

class MemberUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    member_level: Optional[str] = Field(None, regex="^(basic|silver|gold|platinum)$")
    remaining_sessions: Optional[int] = Field(None, ge=0)
    expiry_date: Optional[datetime] = None
    is_active: Optional[bool] = None

    @validator('phone')
    def validate_phone(cls, v):
        if v and not re.match(r'^\+?[1-9]\d{1,14}$', v):
            raise ValueError('Invalid phone number format')
        return v

    @validator('email')
    def validate_email(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v

class MemberInDB(MemberBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class MemberResponse(MemberInDB):
    pass

class MemberListResponse(BaseModel):
    members: list[MemberResponse]
    total: int
    page: int
    size: int

class MemberQuery(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    member_card_number: Optional[str] = None
    member_level: Optional[str] = None
    is_active: Optional[bool] = None
    page: int = Field(default=1, ge=1)
    size: int = Field(default=10, ge=1, le=100)

    @validator('member_level')
    def validate_member_level(cls, v):
        if v and v not in ['basic', 'silver', 'gold', 'platinum']:
            raise ValueError('Invalid member level')
        return v
