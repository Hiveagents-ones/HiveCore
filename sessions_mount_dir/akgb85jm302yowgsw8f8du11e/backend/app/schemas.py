from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

# Base schemas
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# Member schemas
class MemberBase(BaseSchema):
    username: str
    email: EmailStr
    membership_level: str = 'basic'
    expiry_date: Optional[datetime] = None
    is_active: bool = True

class MemberCreate(MemberBase):
    password: str

class MemberUpdate(BaseSchema):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    membership_level: Optional[str] = None
    expiry_date: Optional[datetime] = None
    is_active: Optional[bool] = None

class MemberResponse(MemberBase):
    id: int
    created_at: datetime
    updated_at: datetime

# Package schemas
class PackageBase(BaseSchema):
    name: str
    description: Optional[str] = None
    duration_months: int
    price: Decimal
    is_active: bool = True

class PackageCreate(PackageBase):
    pass

class PackageUpdate(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_months: Optional[int] = None
    price: Optional[Decimal] = None
    is_active: Optional[bool] = None

class PackageResponse(PackageBase):
    id: int
    created_at: datetime
    updated_at: datetime

# Order schemas
class OrderBase(BaseSchema):
    amount: Decimal
    status: str = 'pending'

class OrderCreate(OrderBase):
    package_id: int

class OrderUpdate(BaseSchema):
    status: Optional[str] = None

class OrderResponse(OrderBase):
    id: int
    member_id: int
    package_id: int
    order_number: str
    created_at: datetime
    updated_at: datetime
    member: Optional[MemberResponse] = None
    package: Optional[PackageResponse] = None

# Payment schemas
class PaymentBase(BaseSchema):
    payment_method: str
    amount: Decimal
    status: str = 'pending'
    transaction_id: Optional[str] = None

class PaymentCreate(PaymentBase):
    order_id: int

class PaymentUpdate(BaseSchema):
    status: Optional[str] = None
    transaction_id: Optional[str] = None
    gateway_response: Optional[str] = None

class PaymentResponse(PaymentBase):
    id: int
    order_id: int
    member_id: int
    created_at: datetime
    updated_at: datetime
    gateway_response: Optional[str] = None

# Membership status response
class MembershipStatusResponse(BaseSchema):
    member: MemberResponse
    available_packages: List[PackageResponse]
    active_orders: List[OrderResponse] = []

# Renewal request
class RenewalRequest(BaseSchema):
    package_id: int
    payment_method: str

# Renewal response
class RenewalResponse(BaseSchema):
    order: OrderResponse
    payment: Optional[PaymentResponse] = None
    message: str