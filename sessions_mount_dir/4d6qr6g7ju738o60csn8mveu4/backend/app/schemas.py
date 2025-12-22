from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
from enum import Enum

class MembershipType(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

class MemberBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="会员姓名")
    phone: str = Field(..., regex=r"^1[3-9]\d{9}$", description="手机号")
    id_card: str = Field(..., regex=r"^\d{17}[\dXx]$", description="身份证号")
    membership_type: MembershipType = Field(..., description="会员卡类型")
    privacy_policy_accepted: bool = Field(..., description="是否同意隐私政策")
    
    @validator('privacy_policy_accepted')
    def validate_privacy_policy(cls, v):
        if not v:
            raise ValueError('必须同意隐私政策才能注册')
        return v

class MemberCreate(MemberBase):
    pass

class MemberUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    phone: Optional[str] = Field(None, regex=r"^1[3-9]\d{9}$")
    membership_type: Optional[MembershipType] = None
    privacy_policy_accepted: Optional[bool] = None
    
    @validator('privacy_policy_accepted')
    def validate_privacy_policy(cls, v):
        if v is not None and not v:
            raise ValueError('必须同意隐私政策')
        return v

class MemberInDB(MemberBase):
    id: int
    member_id: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    
    class Config:
        orm_mode = True

class Member(MemberInDB):
    pass

class MemberResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Member] = None
    
    class Config:
        orm_mode = True

class MembersListResponse(BaseModel):
    success: bool
    message: str
    data: list[Member]
    total: int
    page: int
    per_page: int
    
    class Config:
        orm_mode = True

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[dict] = None
