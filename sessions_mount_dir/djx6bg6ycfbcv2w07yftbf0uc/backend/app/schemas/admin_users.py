from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: str = Field(..., description="邮箱地址")
    is_active: bool = Field(True, description="用户是否激活")
    is_banned: bool = Field(False, description="用户是否被封禁")


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100, description="密码")


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="用户名")
    email: Optional[str] = Field(None, description="邮箱地址")
    is_active: Optional[bool] = Field(None, description="用户是否激活")
    is_banned: Optional[bool] = Field(None, description="用户是否被封禁")


class UserInDB(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserResponse(UserInDB):
    pass


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int
    page: int
    size: int


class BanUserRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500, description="封禁原因")
    duration_days: Optional[int] = Field(None, ge=1, le=365, description="封禁天数，不填则永久封禁")


class UnbanUserRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500, description="解封原因")


class UserAppeal(BaseModel):
    id: int
    user_id: int
    reason: str = Field(..., min_length=1, max_length=1000, description="申诉原因")
    status: str = Field(..., description="申诉状态: pending/approved/rejected")
    created_at: datetime
    updated_at: datetime
    response: Optional[str] = Field(None, description="管理员回复")

    class Config:
        from_attributes = True


class AppealResponse(BaseModel):
    appeal: UserAppeal
    user: UserResponse


class AppealListResponse(BaseModel):
    appeals: list[AppealResponse]
    total: int
    page: int
    size: int


class ProcessAppealRequest(BaseModel):
    status: str = Field(..., description="处理结果: approved/rejected")
    response: str = Field(..., min_length=1, max_length=1000, description="处理回复")
