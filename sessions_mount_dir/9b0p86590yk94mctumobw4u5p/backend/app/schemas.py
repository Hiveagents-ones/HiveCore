from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum

from .models import UserStatus, PlanType, OrderStatus

class UserStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class PlanTypeEnum(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"

class OrderStatusEnum(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

# Base schemas
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# User schemas
class UserBase(BaseSchema):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool = True
    status: UserStatusEnum = UserStatusEnum.ACTIVE

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseSchema):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[UserStatusEnum] = None

class User(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    membership_expires_at: Optional[datetime] = None
    is_premium: bool = False
    stripe_customer_id: Optional[str] = None

# Plan schemas
class PlanBase(BaseSchema):
    name: str
    description: Optional[str] = None
    type: PlanTypeEnum
    price: int
    currency: str = "USD"
    duration_days: Optional[int] = None
    features: Optional[str] = None
    is_active: bool = True

class PlanCreate(PlanBase):
    stripe_price_id: str

class PlanUpdate(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[PlanTypeEnum] = None
    price: Optional[int] = None
    currency: Optional[str] = None
    duration_days: Optional[int] = None
    features: Optional[str] = None
    is_active: Optional[bool] = None
    stripe_price_id: Optional[str] = None

class Plan(PlanBase):
    id: int
    stripe_price_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

# Order schemas
class OrderBase(BaseSchema):
    plan_id: int
    amount: int
    currency: str = "USD"
    status: OrderStatusEnum = OrderStatusEnum.PENDING

class OrderCreate(OrderBase):
    stripe_payment_intent_id: str

class OrderUpdate(BaseSchema):
    status: Optional[OrderStatusEnum] = None
    stripe_payment_intent_id: Optional[str] = None

class Order(OrderBase):
    id: int
    user_id: int
    stripe_payment_intent_id: Optional[str] = None
    created_at: datetime
    user: Optional[User] = None
    plan: Optional[Plan] = None

# Subscription schemas
class SubscriptionBase(BaseSchema):
    plan_id: int
    status: str

class SubscriptionCreate(SubscriptionBase):
    pass

class SubscriptionUpdate(BaseSchema):
    status: Optional[str] = None

class Subscription(SubscriptionBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    user: Optional[User] = None
    plan: Optional[Plan] = None

# Response schemas
class UserResponse(BaseSchema):
    id: int
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    status: UserStatusEnum
    created_at: datetime
    updated_at: Optional[datetime] = None
    membership_expires_at: Optional[datetime] = None
    is_premium: bool
    orders: List[Order] = []
    subscriptions: List[Subscription] = []

class PlanResponse(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    type: PlanTypeEnum
    price: int
    currency: str
    duration_days: Optional[int] = None
    features: Optional[str] = None
    is_active: bool
    stripe_price_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    orders: List[Order] = []
    subscriptions: List[Subscription] = []

class OrderResponse(BaseSchema):
    id: int
    user_id: int
    plan_id: int
    amount: int
    currency: str
    status: OrderStatusEnum
    stripe_payment_intent_id: Optional[str] = None
    created_at: datetime
    user: Optional[User] = None
    plan: Optional[Plan] = None

class SubscriptionResponse(BaseSchema):
    id: int
    user_id: int
    plan_id: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    user: Optional[User] = None
    plan: Optional[Plan] = None

# Membership status response
class MembershipStatusResponse(BaseSchema):
    is_premium: bool
    membership_expires_at: Optional[datetime] = None
    days_until_expiry: Optional[int] = None
    is_expired: bool = False
    can_renew: bool = True
    current_plan: Optional[Plan] = None
    available_plans: List[Plan] = []

# Payment schemas
class PaymentIntentCreate(BaseSchema):
    plan_id: int

class PaymentIntentResponse(BaseSchema):
    client_secret: str
    payment_intent_id: str
    amount: int
    currency: str
    plan: Plan

# Renewal schemas
class RenewalRequest(BaseSchema):
    plan_id: int

class RenewalResponse(BaseSchema):
    order: Order
    payment_intent: PaymentIntentResponse
    new_expiry_date: datetime