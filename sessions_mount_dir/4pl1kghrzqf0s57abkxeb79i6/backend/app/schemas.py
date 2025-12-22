from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List
from enum import Enum

class GenderEnum(str, Enum):
    male = "male"
    female = "female"
    other = "other"

class MembershipStatusEnum(str, Enum):
    active = "active"
    frozen = "frozen"
    expired = "expired"

class MembershipTypeEnum(str, Enum):
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"

class BookingStatusEnum(str, Enum):
    booked = "booked"
    cancelled = "cancelled"
    completed = "completed"

class PaymentTypeEnum(str, Enum):
    membership = "membership"
    course = "course"
    personal_training = "personal_training"
    other = "other"

class PaymentMethodEnum(str, Enum):
    cash = "cash"
    card = "card"
    online = "online"

# Member Schemas
class MemberBase(BaseModel):
    name: str
    gender: GenderEnum
    age: int
    phone: str
    email: Optional[EmailStr] = None
    membership_type: MembershipTypeEnum
    membership_status: Optional[MembershipStatusEnum] = MembershipStatusEnum.active
    fitness_goal: Optional[str] = None

class MemberCreate(MemberBase):
    membership_end: Optional[datetime] = None

class MemberUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[GenderEnum] = None
    age: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    membership_type: Optional[MembershipTypeEnum] = None
    membership_status: Optional[MembershipStatusEnum] = None
    membership_end: Optional[datetime] = None
    fitness_goal: Optional[str] = None

class Member(MemberBase):
    id: int
    membership_start: datetime
    membership_end: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# MemberCard Schemas
class MemberCardBase(BaseModel):
    card_number: str
    card_type: MembershipTypeEnum
    status: Optional[MembershipStatusEnum] = MembershipStatusEnum.active
    expiry_date: datetime

class MemberCardCreate(MemberCardBase):
    member_id: int

class MemberCardUpdate(BaseModel):
    card_type: Optional[MembershipTypeEnum] = None
    status: Optional[MembershipStatusEnum] = None
    expiry_date: Optional[datetime] = None

class MemberCard(MemberCardBase):
    id: int
    member_id: int
    issue_date: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# AccessRecord Schemas
class AccessRecordBase(BaseModel):
    access_type: str  # 'entry' or 'exit'

class AccessRecordCreate(AccessRecordBase):
    member_id: int

class AccessRecord(AccessRecordBase):
    id: int
    member_id: int
    access_time: datetime
    created_at: datetime

    class Config:
        from_attributes = True

# Batch Operations Schemas
class MemberBatchImport(BaseModel):
    members: List[MemberCreate]

class MemberBatchExport(BaseModel):
    member_ids: List[int]

# Membership Renewal Schemas
class MembershipRenewal(BaseModel):
    membership_type: MembershipTypeEnum
    duration_months: int

# Response Schemas
class MemberResponse(BaseModel):
    success: bool
    data: Optional[Member] = None
    message: str

class MembersResponse(BaseModel):
    success: bool
    data: List[Member]
    message: str
    total: Optional[int] = None

class MemberCardResponse(BaseModel):
    success: bool
    data: Optional[MemberCard] = None
    message: str

class AccessRecordsResponse(BaseModel):
    success: bool
    data: List[AccessRecord]
    message: str
    total: Optional[int] = None

class BatchOperationResponse(BaseModel):
    success: bool
    processed: int
    failed: int
    errors: List[str] = []
    message: str

class MembershipRenewalResponse(BaseModel):
    success: bool
    data: Optional[Member] = None
    message: str
    new_expiry_date: Optional[datetime] = None