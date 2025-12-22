from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class MemberBase(BaseModel):
    name: str = Field(..., max_length=100, description="会员姓名")
    phone: str = Field(..., max_length=20, description="手机号码")
    email: Optional[str] = Field(None, max_length=100, description="电子邮箱")
    level: str = Field(default="普通会员", max_length=20, description="会员等级")
    points: int = Field(default=0, ge=0, description="会员积分")
    remaining_membership: int = Field(default=0, ge=0, description="剩余会籍(月)")
    is_active: bool = Field(default=True, description="是否激活")
    notes: Optional[str] = Field(None, description="备注信息")

    @validator('phone')
    def validate_phone(cls, v):
        if not v.isdigit():
            raise ValueError('手机号码必须为数字')
        if len(v) not in [10, 11]:
            raise ValueError('手机号码长度必须为10或11位')
        return v

    @validator('email')
    def validate_email(cls, v):
        if v is not None and '@' not in v:
            raise ValueError('电子邮箱格式不正确')
        return v


class MemberCreate(MemberBase):
    pass


class MemberUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="会员姓名")
    phone: Optional[str] = Field(None, max_length=20, description="手机号码")
    email: Optional[str] = Field(None, max_length=100, description="电子邮箱")
    level: Optional[str] = Field(None, max_length=20, description="会员等级")
    points: Optional[int] = Field(None, ge=0, description="会员积分")
    remaining_membership: Optional[int] = Field(None, ge=0, description="剩余会籍(月)")
    is_active: Optional[bool] = Field(None, description="是否激活")
    notes: Optional[str] = Field(None, description="备注信息")

    @validator('phone')
    def validate_phone(cls, v):
        if v is not None:
            if not v.isdigit():
                raise ValueError('手机号码必须为数字')
            if len(v) not in [10, 11]:
                raise ValueError('手机号码长度必须为10或11位')
        return v

    @validator('email')
    def validate_email(cls, v):
        if v is not None and '@' not in v:
            raise ValueError('电子邮箱格式不正确')
        return v


class MemberInDB(MemberBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class Member(MemberInDB):
    pass


class MemberResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str]
    level: str
    points: int
    remaining_membership: int
    is_active: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class MemberListResponse(BaseModel):
    members: list[MemberResponse]
    total: int
    page: int
    size: int
