from datetime import date
from typing import Optional
from pydantic import BaseModel, EmailStr
from pydantic import validator, Field
from pydantic import root_validator
from pydantic import ConfigDict


class MemberBase(BaseModel):
    model_config = ConfigDict(extra='allow', json_schema_extra={
        "example": {
            "name": "John Doe",
            "phone": "+8613812345678",
            "email": "john@example.com",
            "level": "basic",
            "points": 0,
            "join_date": "2023-01-01",
            "custom_fields": {"preferred_branch": "downtown"}
        }
    })
    
    custom_fields: Optional[dict] = Field(default_factory=dict, description="Additional member attributes")
    level: str = Field(default="basic", description="Member level (basic, silver, gold, platinum)")
    points: int = Field(default=0, ge=0, description="Loyalty points accumulated")
    name: str = Field(..., min_length=2, max_length=100, description="Member full name")
    phone: str = Field(..., regex=r"^\+?[1-9]\d{1,14}$", description="Phone number in E.164 format")
    email: EmailStr = Field(..., description="Valid email address")
    join_date: date = Field(default_factory=date.today, description="Date when member joined")
    
    @validator('level')
    def validate_level(cls, v):
        if v not in ["basic", "silver", "gold", "platinum"]:
            raise ValueError("Invalid member level")
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
    @root_validator
    def validate_custom_fields(cls, values):
        """
        Validate custom fields structure and values
        Rules:
        1. Field names must be snake_case
        2. Values must be JSON serializable
        3. No nested objects deeper than 2 levels
        """
        custom_fields = values.get('custom_fields', {})
        
        for field_name, field_value in custom_fields.items():
            # Validate field name format
            if not isinstance(field_name, str) or not field_name.isidentifier() or not field_name.islower():
                raise ValueError(f"Invalid custom field name '{field_name}'. Must be snake_case identifier")
            
            # Validate field value type
            if isinstance(field_value, (dict, list)):
                if isinstance(field_value, dict) and any(isinstance(v, (dict, list)) for v in field_value.values()):
                    raise ValueError(f"Nested structures in custom field '{field_name}' exceed maximum depth")
                if isinstance(field_value, list) and any(isinstance(v, (dict, list)) for v in field_value):
                    raise ValueError(f"Nested structures in custom field '{field_name}' exceed maximum depth")
            
        return values
        if not v.startswith('+'):
            v = f"+86{v}"  # Default to China country code if not specified
        return v


class MemberCreate(MemberBase):
    pass


class MemberUpdate(BaseModel):
    custom_fields: Optional[dict] = Field(None, description="Additional member attributes")
    level: Optional[str] = Field(None, description="Member level (basic, silver, gold, platinum)")
    points: Optional[int] = Field(None, ge=0, description="Loyalty points accumulated")
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="Member full name")
    phone: Optional[str] = Field(None, regex=r"^\+?[1-9]\d{1,14}$", description="Phone number in E.164 format")
    email: Optional[EmailStr] = Field(None, description="Valid email address")


class Member(MemberBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 1,
            "name": "John Doe",
            "phone": "+8613812345678",
            "email": "john@example.com",
            "level": "basic",
            "points": 100,
            "join_date": "2023-01-01",
            "custom_fields": {"preferred_branch": "downtown"}
        }
    })


class MemberCardBase(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "card_number": "1234567890123456",
            "status": "active",
            "expiry_date": "2025-12-31"
        }
    })
    
    card_number: str = Field(..., min_length=16, max_length=19, description="Card number (16-19 digits)")
    status: str = Field(..., description="Card status (active, expired, lost, stolen)")
    expiry_date: date = Field(..., description="Card expiration date")
    
    @validator('status')
    def validate_status(cls, v):
        if v not in ["active", "expired", "lost", "stolen"]:
            raise ValueError("Invalid card status")
        return v
    
    @validator('card_number')
    def validate_card_number(cls, v):
        if not v.isdigit():
            raise ValueError("Card number must contain only digits")
        return v


class MemberCardCreate(MemberCardBase):
    member_id: int


class MemberCardUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Card status (active, expired, lost, stolen)")
    expiry_date: Optional[date] = Field(None, description="Card expiration date")


class MemberCard(MemberCardBase):
    id: int
    member_id: int
    
    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 1,
            "member_id": 1,
            "card_number": "1234567890123456",
            "status": "active",
            "expiry_date": "2025-12-31"
        }
    })