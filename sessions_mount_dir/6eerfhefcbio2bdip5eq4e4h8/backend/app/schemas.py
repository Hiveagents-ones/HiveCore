from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

class MemberLevel(str, Enum):
    """会员等级枚举"""
    ORDINARY = "普通"
    SILVER = "银卡"
    GOLD = "金卡"
    PLATINUM = "白金"
    DIAMOND = "钻石"

class MemberBase(BaseModel):
    """会员基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="会员姓名")
    phone: str = Field(..., min_length=1, max_length=20, description="手机号码")
    email: Optional[str] = Field(None, max_length=100, description="电子邮箱")
    level: MemberLevel = Field(default=MemberLevel.ORDINARY, description="会员等级")
    start_date: datetime = Field(default_factory=datetime.utcnow, description="生效日期")
    end_date: Optional[datetime] = Field(None, description="到期日期")
    status: bool = Field(default=True, description="会员状态")
    custom_fields: Optional[Dict[str, Any]] = Field(default=None, description="自定义字段")

    @validator('email')
    def validate_email(cls, v):
        if v is not None and '@' not in v:
            raise ValueError('Invalid email format')
        return v

class MemberCreate(MemberBase):
    """创建会员请求模型"""
    pass

class MemberUpdate(BaseModel):
    """更新会员请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="会员姓名")
    phone: Optional[str] = Field(None, min_length=1, max_length=20, description="手机号码")
    email: Optional[str] = Field(None, max_length=100, description="电子邮箱")
    level: Optional[MemberLevel] = Field(None, description="会员等级")
    start_date: Optional[datetime] = Field(None, description="生效日期")
    end_date: Optional[datetime] = Field(None, description="到期日期")
    status: Optional[bool] = Field(None, description="会员状态")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="自定义字段")

    @validator('email')
    def validate_email(cls, v):
        if v is not None and '@' not in v:
            raise ValueError('Invalid email format')
        return v

class MemberResponse(MemberBase):
    """会员响应模型"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=1, max_length=50, description="用户名")
    email: str = Field(..., description="邮箱")
    is_active: bool = Field(default=True, description="是否激活")
    is_superuser: bool = Field(default=False, description="是否超级用户")

class UserCreate(UserBase):
    """创建用户请求模型"""
    password: str = Field(..., min_length=6, description="密码")

class UserUpdate(BaseModel):
    """更新用户请求模型"""
    username: Optional[str] = Field(None, min_length=1, max_length=50, description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    password: Optional[str] = Field(None, min_length=6, description="密码")
    is_active: Optional[bool] = Field(None, description="是否激活")
    is_superuser: Optional[bool] = Field(None, description="是否超级用户")

class UserResponse(UserBase):
    """用户响应模型"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    """令牌模型"""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """令牌数据模型"""
    username: Optional[str] = None

class AuditLogBase(BaseModel):
    """审计日志基础模型"""
    action: str = Field(..., description="操作类型")
    details: Optional[Dict[str, Any]] = Field(None, description="操作详情")
    ip_address: Optional[str] = Field(None, description="IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")

class AuditLogCreate(AuditLogBase):
    """创建审计日志请求模型"""
    member_id: int = Field(..., description="会员ID")
    user_id: int = Field(..., description="用户ID")

class AuditLogResponse(AuditLogBase):
    """审计日志响应模型"""
    id: int
    member_id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class PaginationParams(BaseModel):
    """分页参数模型"""
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=10, ge=1, le=100, description="每页数量")

class PaginatedResponse(BaseModel):
    """分页响应模型"""
    items: list
    total: int
    page: int
    size: int
    pages: int
