from pydantic import BaseModel, Field, validator
from typing import Optional
import re
from datetime import datetime

class MemberRegisterRequest(BaseModel):
    """会员注册请求模型"""
    name: str = Field(..., min_length=2, max_length=50, description="姓名")
    phone: str = Field(..., description="手机号")
    id_card: str = Field(..., description="身份证号")
    email: Optional[str] = Field(None, description="邮箱")
    gender: Optional[str] = Field(None, description="性别")
    birth_date: Optional[str] = Field(None, description="出生日期")
    address: Optional[str] = Field(None, max_length=200, description="地址")
    emergency_contact: Optional[str] = Field(None, description="紧急联系人")
    emergency_phone: Optional[str] = Field(None, description="紧急联系人电话")
    
    @validator('phone')
    def validate_phone(cls, v):
        if not re.match(r'^1[3-9]\d{9}$', v):
            raise ValueError('手机号格式不正确')
        return v
    
    @validator('id_card')
    def validate_id_card(cls, v):
        if not re.match(r'^\d{17}[\dXx]$', v):
            raise ValueError('身份证号格式不正确')
        return v
    
    @validator('email')
    def validate_email(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('邮箱格式不正确')
        return v
    
    @validator('gender')
    def validate_gender(cls, v):
        if v and v not in ['男', '女', 'M', 'F']:
            raise ValueError('性别只能是男、女、M或F')
        return v
    
    @validator('birth_date')
    def validate_birth_date(cls, v):
        if v:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('出生日期格式应为YYYY-MM-DD')
        return v
    
    @validator('emergency_phone')
    def validate_emergency_phone(cls, v):
        if v and not re.match(r'^1[3-9]\d{9}$', v):
            raise ValueError('紧急联系人电话格式不正确')
        return v

class MemberRegisterResponse(BaseModel):
    """会员注册响应模型"""
    success: bool = Field(..., description="注册是否成功")
    message: str = Field(..., description="响应消息")
    member_id: Optional[str] = Field(None, description="会员ID")
    member_account: Optional[str] = Field(None, description="会员账号")
    registration_time: Optional[datetime] = Field(None, description="注册时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S')
        }

class MemberInfoResponse(BaseModel):
    """会员信息响应模型"""
    member_id: str = Field(..., description="会员ID")
    member_account: str = Field(..., description="会员账号")
    name: str = Field(..., description="姓名")
    phone: str = Field(..., description="手机号")
    email: Optional[str] = Field(None, description="邮箱")
    gender: Optional[str] = Field(None, description="性别")
    birth_date: Optional[str] = Field(None, description="出生日期")
    address: Optional[str] = Field(None, description="地址")
    emergency_contact: Optional[str] = Field(None, description="紧急联系人")
    emergency_phone: Optional[str] = Field(None, description="紧急联系人电话")
    registration_time: datetime = Field(..., description="注册时间")
    status: str = Field(..., description="会员状态")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S')
        }

class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = Field(False, description="请求是否成功")
    error_code: str = Field(..., description="错误代码")
    error_message: str = Field(..., description="错误信息")
    details: Optional[dict] = Field(None, description="错误详情")