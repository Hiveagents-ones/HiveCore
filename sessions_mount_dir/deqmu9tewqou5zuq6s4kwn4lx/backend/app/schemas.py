from pydantic import BaseModel, Decimal
from datetime import datetime
from typing import Optional

# Base schemas
class BaseSchema(BaseModel):
    class Config:
        orm_mode = True

# User schemas
class UserBase(BaseSchema):
    username: str
    email: str
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseSchema):
    username: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None

class User(UserBase):
    id: int
    created_at: datetime

# Membership Plan schemas
class MembershipPlanBase(BaseSchema):
    name: str
    description: str
    price: Decimal
    duration_months: int
    is_active: bool = True

class MembershipPlanCreate(MembershipPlanBase):
    pass

class MembershipPlanUpdate(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    duration_months: Optional[int] = None
    is_active: Optional[bool] = None

class MembershipPlan(MembershipPlanBase):
    id: int
    created_at: datetime
    updated_at: datetime

# Membership Record schemas
class MembershipRecordBase(BaseSchema):
    start_date: datetime
    end_date: datetime
    is_active: bool = True

class MembershipRecordCreate(MembershipRecordBase):
    user_id: int

class MembershipRecordUpdate(BaseSchema):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None

class MembershipRecord(MembershipRecordBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

# Subscription Record schemas
class SubscriptionRecordBase(BaseSchema):
    amount_paid: Decimal
    payment_method: str
    transaction_id: str
    status: str = "completed"

class SubscriptionRecordCreate(SubscriptionRecordBase):
    user_id: int
    plan_id: int
    start_date: datetime
    end_date: datetime

class SubscriptionRecordUpdate(BaseSchema):
    amount_paid: Optional[Decimal] = None
    payment_method: Optional[str] = None
    status: Optional[str] = None

class SubscriptionRecord(SubscriptionRecordBase):
    id: int
    user_id: int
    plan_id: int
    payment_date: datetime
    start_date: datetime
    end_date: datetime
    created_at: datetime
    plan: MembershipPlan

# Response schemas with relationships
class UserWithMembership(User):
    membership_records: list[MembershipRecord] = []
    subscription_records: list[SubscriptionRecord] = []

class MembershipPlanWithSubscriptions(MembershipPlan):
    subscription_records: list[SubscriptionRecord] = []

class MembershipRecordWithUser(MembershipRecord):
    user: User

class SubscriptionRecordWithDetails(SubscriptionRecord):
    user: User
    plan: MembershipPlan
