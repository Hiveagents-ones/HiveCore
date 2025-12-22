from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from typing import List

class MemberBase(BaseModel):
    name: str = Field(..., max_length=100, description="会员姓名")
    email: EmailStr = Field(..., description="会员邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="会员电话")
    membership_level: str = Field(default="basic", max_length=50, description="会员等级")
    remaining_membership: int = Field(default=0, ge=0, description="剩余会籍")
    is_active: bool = Field(default=True, description="会员状态")

class MemberCreate(MemberBase):
    pass

class MemberUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="会员姓名")
    email: Optional[EmailStr] = Field(None, description="会员邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="会员电话")
    membership_level: Optional[str] = Field(None, max_length=50, description="会员等级")
    remaining_membership: Optional[int] = Field(None, ge=0, description="剩余会籍")
    is_active: Optional[bool] = Field(None, description="会员状态")

class MemberInDB(MemberBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class Member(MemberInDB):
    pass

class MemberList(BaseModel):
    members: List[Member]
    total: int
    page: int
    per_page: int

class AuditLogBase(BaseModel):
    action: str = Field(..., max_length=100, description="操作类型")
    old_values: Optional[str] = Field(None, description="旧值")
    new_values: Optional[str] = Field(None, description="新值")

class AuditLogCreate(AuditLogBase):
    member_id: int

class AuditLogInDB(AuditLogBase):
    id: int
    member_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class AuditLog(AuditLogInDB):
    pass

class MemberWithAuditLogs(Member):
    audit_logs: List[AuditLog] = Field(default_factory=list, description="审计日志")
