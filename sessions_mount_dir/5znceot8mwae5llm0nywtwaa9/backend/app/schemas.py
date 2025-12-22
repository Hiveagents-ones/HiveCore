from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import re


class MemberRegisterRequest(BaseModel):
    """Schema for member registration request"""
    name: str = Field(..., min_length=2, max_length=50, description="Member's full name")
    phone: str = Field(..., description="Member's phone number")
    id_card: str = Field(..., description="Member's ID card number")
    membership_plan_id: int = Field(..., description="Selected membership plan ID")
    
    @validator('phone')
    def validate_phone(cls, v):
        if not re.match(r'^1[3-9]\d{9}$', v):
            raise ValueError('Invalid phone number format')
        return v
    
    @validator('id_card')
    def validate_id_card(cls, v):
        if not re.match(r'^\d{17}[\dXx]$', v):
            raise ValueError('Invalid ID card number format')
        return v


class MemberResponse(BaseModel):
    """Schema for member response"""
    id: int
    name: str
    phone: str
    id_card: str
    membership_plan_id: int
    account_number: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Schema for error response"""
    detail: str
    error_code: Optional[str] = None


class SuccessResponse(BaseModel):
    """Schema for success response"""
    message: str
    data: Optional[dict] = None