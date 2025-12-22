from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
import re


class MemberBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="会员姓名")
    phone_number: str = Field(..., min_length=1, max_length=20, description="手机号码")
    id_card_number: str = Field(..., min_length=1, max_length=18, description="身份证号")
    health_status: Optional[str] = Field(None, description="健康状况")
    address: Optional[str] = Field(None, max_length=200, description="地址")
    email: Optional[str] = Field(None, max_length=100, description="电子邮箱")

    @validator('phone_number')
    def validate_phone_number(cls, v):
        if not re.match(r'^1[3-9]\d{9}$', v):
            raise ValueError('手机号码格式不正确')
        return v

    @validator('id_card_number')
    def validate_id_card_number(cls, v):
        if not re.match(r'^\d{17}[\dXx]$', v):
            raise ValueError('身份证号格式不正确')
        return v

    @validator('email')
    def validate_email(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('电子邮箱格式不正确')
        return v


class MemberCreate(MemberBase):
    pass


class MemberUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="会员姓名")
    phone_number: Optional[str] = Field(None, min_length=1, max_length=20, description="手机号码")
    id_card_number: Optional[str] = Field(None, min_length=1, max_length=18, description="身份证号")
    health_status: Optional[str] = Field(None, description="健康状况")
    address: Optional[str] = Field(None, max_length=200, description="地址")
    email: Optional[str] = Field(None, max_length=100, description="电子邮箱")

    @validator('phone_number')
    def validate_phone_number(cls, v):
        if v and not re.match(r'^1[3-9]\d{9}$', v):
            raise ValueError('手机号码格式不正确')
        return v

    @validator('id_card_number')
    def validate_id_card_number(cls, v):
        if v and not re.match(r'^\d{17}[\dXx]$', v):
            raise ValueError('身份证号格式不正确')
        return v

    @validator('email')
    def validate_email(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('电子邮箱格式不正确')
        return v


class MemberInDB(MemberBase):
    id: int
    registration_date: datetime
    last_updated: datetime

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
    name: Optional[str] = Field(None, description="按姓名查询")
    phone_number: Optional[str] = Field(None, description="按手机号查询")
    id_card_number: Optional[str] = Field(None, description="按身份证号查询")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(10, ge=1, le=100, description="每页数量")

    @validator('phone_number')
    def validate_phone_number(cls, v):
        if v and not re.match(r'^1[3-9]\d{9}$', v):
            raise ValueError('手机号码格式不正确')
        return v

    @validator('id_card_number')
    def validate_id_card_number(cls, v):
        if v and not re.match(r'^\d{17}[\dXx]$', v):
            raise ValueError('身份证号格式不正确')
        return v
