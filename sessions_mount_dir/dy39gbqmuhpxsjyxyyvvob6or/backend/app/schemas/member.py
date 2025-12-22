from datetime import date
from typing import Optional
from pydantic import BaseModel, EmailStr
from enum import Enum
from pydantic import Field


class MemberBase(BaseModel):
    """会员基础模型"""
    name: str
    email: EmailStr
    phone: str
    join_date: date


class MemberCreate(MemberBase):
    """会员创建模型"""
    pass


class MemberUpdate(BaseModel):
    """会员更新模型"""
    status: Optional[MemberStatus] = None
    membership_expiry: Optional[date] = None
    """会员更新模型"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class Member(MemberBase):
    """会员数据库模型"""
    id: int

    class Config:
        orm_mode = True


class MemberOut(Member):
    """会员输出模型"""
    pass


class MemberStatus(str, Enum):
    """会员状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class MemberWithStatus(Member):
    """带状态的会员模型"""
    status: MemberStatus = Field(default=MemberStatus.ACTIVE, description="会员状态")
    membership_expiry: Optional[date] = Field(default=None, description="会员到期日")
    class Config:
        orm_mode = True