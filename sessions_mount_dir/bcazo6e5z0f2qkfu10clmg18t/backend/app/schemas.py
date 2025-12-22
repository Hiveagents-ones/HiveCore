from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
import re

class MemberRegisterRequest(BaseModel):
    """会员注册请求模型"""
    name: str = Field(..., min_length=2, max_length=50, description="会员姓名")
    phone: str = Field(..., description="手机号码")
    id_card: str = Field(..., description="身份证号")
    email: Optional[str] = Field(None, description="电子邮箱")
    address: Optional[str] = Field(None, max_length=200, description="联系地址")
    emergency_contact: Optional[str] = Field(None, max_length=50, description="紧急联系人")
    emergency_phone: Optional[str] = Field(None, description="紧急联系电话")
    
    @validator('phone')
    def validate_phone(cls, v):
        if not re.match(r'^1[3-9]\d{9}$', v):
            raise ValueError('手机号码格式不正确')
        return v
    
    @validator('id_card')
    def validate_id_card(cls, v):
        if not re.match(r'^\d{17}[\dXx]$', v):
            raise ValueError('身份证号格式不正确')
        return v
    
    @validator('email')
    def validate_email(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('电子邮箱格式不正确')
        return v
    
    @validator('emergency_phone')
    def validate_emergency_phone(cls, v):
        if v and not re.match(r'^1[3-9]\d{9}$', v):
            raise ValueError('紧急联系电话格式不正确')
        return v

class MemberRegisterResponse(BaseModel):
    """会员注册响应模型"""
    member_id: str = Field(..., description="会员ID")
    name: str = Field(..., description="会员姓名")
    phone: str = Field(..., description="手机号码")
    registration_date: datetime = Field(..., description="注册日期")
    status: str = Field(..., description="会员状态")
    
    class Config:
        from_attributes = True

class MemberResponse(BaseModel):
    """会员信息响应模型"""
    member_id: str = Field(..., description="会员ID")
    name: str = Field(..., description="会员姓名")
    phone: str = Field(..., description="手机号码")
    id_card: str = Field(..., description="身份证号")
    email: Optional[str] = Field(None, description="电子邮箱")
    address: Optional[str] = Field(None, description="联系地址")
    emergency_contact: Optional[str] = Field(None, description="紧急联系人")
    emergency_phone: Optional[str] = Field(None, description="紧急联系电话")
    registration_date: datetime = Field(..., description="注册日期")
    status: str = Field(..., description="会员状态")
    
    class Config:
        from_attributes = True

class MemberUpdateRequest(BaseModel):
    """会员信息更新请求模型"""
    name: Optional[str] = Field(None, min_length=2, max_length=50, description="会员姓名")
    phone: Optional[str] = Field(None, description="手机号码")
    email: Optional[str] = Field(None, description="电子邮箱")
    address: Optional[str] = Field(None, max_length=200, description="联系地址")
    emergency_contact: Optional[str] = Field(None, max_length=50, description="紧急联系人")
    emergency_phone: Optional[str] = Field(None, description="紧急联系电话")
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and not re.match(r'^1[3-9]\d{9}$', v):
            raise ValueError('手机号码格式不正确')
        return v
    
    @validator('email')
    def validate_email(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('电子邮箱格式不正确')
        return v
    
    @validator('emergency_phone')
    def validate_emergency_phone(cls, v):
        if v and not re.match(r'^1[3-9]\d{9}$', v):
            raise ValueError('紧急联系电话格式不正确')
        return v

class MemberStatusUpdateRequest(BaseModel):
    """会员状态更新请求模型"""
    status: str = Field(..., description="会员状态")
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['active', 'inactive', 'suspended', 'expired']
        if v not in allowed_statuses:
            raise ValueError(f'会员状态必须是以下之一: {allowed_statuses}')
        return v

class MemberListResponse(BaseModel):
    """会员列表响应模型"""
    members: list[MemberResponse] = Field(..., description="会员列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    
    class Config:
        from_attributes = True
