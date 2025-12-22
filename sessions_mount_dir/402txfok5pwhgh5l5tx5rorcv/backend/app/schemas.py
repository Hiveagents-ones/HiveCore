from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    STAFF = "staff"
    MEMBER = "member"

class UserBase(BaseModel):
    username: str = Field(..., max_length=50)
    email: str = Field(..., max_length=100)
    role: UserRole = UserRole.MEMBER
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)

class User(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MemberStatus(str, Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    EXPIRED = "expired"

class MemberBase(BaseModel):
    name: str = Field(..., max_length=100)
    contact: str = Field(..., max_length=50)
    level: str = Field(..., max_length=50)
    status: MemberStatus = MemberStatus.ACTIVE

class MemberCreate(MemberBase):
    pass

class MemberUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    contact: Optional[str] = Field(None, max_length=50)
    level: Optional[str] = Field(None, max_length=50)
    status: Optional[MemberStatus] = None

class Member(MemberBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    @validator('*', pre=True)
    def validate_dynamic_fields(cls, v):
        """支持动态字段的序列化"""
        return v

    class Config:
        from_attributes = True
        extra = 'allow'  # 允许额外字段

class MemberStatusLogBase(BaseModel):
    old_status: Optional[MemberStatus] = None
    new_status: MemberStatus
    changed_by: Optional[str] = Field(None, max_length=100)

class MemberStatusLogCreate(MemberStatusLogBase):
    member_id: int

class MemberStatusLog(MemberStatusLogBase):
    id: int
    member_id: int
    changed_at: datetime

    class Config:
        from_attributes = True

class AuditLogBase(BaseModel):
    action: str = Field(..., max_length=100)
    table_name: str = Field(..., max_length=50)
    record_id: int
    old_values: Optional[str] = None
    new_values: Optional[str] = None
    user_id: Optional[int] = None

class AuditLogCreate(AuditLogBase):
    pass

class AuditLog(AuditLogBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

class CourseBase(BaseModel):
    name: str = Field(..., max_length=100)
    coach: str = Field(..., max_length=100)
    time: datetime
    location: str = Field(..., max_length=100)
    capacity: int = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=500)

class CourseCreate(CourseBase):
    pass

class CourseUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    coach: Optional[str] = Field(None, max_length=100)
    time: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=100)
    capacity: Optional[int] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=500)

class Course(CourseBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    @validator('*', pre=True)
    def validate_dynamic_fields(cls, v):
        """支持动态字段的序列化"""
        return v

    class Config:
        from_attributes = True
        extra = 'allow'  # 允许额外字段

class PaymentType(str, Enum):
    MEMBERSHIP = "membership"
    PRIVATE_COURSE = "private_course"
    BOOKING = "booking"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"

class PaymentBase(BaseModel):
    amount: int = Field(..., gt=0)
    type: PaymentType
    status: PaymentStatus = PaymentStatus.PENDING
    description: Optional[str] = Field(None, max_length=200)
    transaction_id: Optional[str] = Field(None, max_length=100)

class PaymentCreate(PaymentBase):
    member_id: int

class Payment(PaymentBase):
    id: int
    member_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    @validator('*', pre=True)
    def validate_dynamic_fields(cls, v):
        """支持动态字段的序列化"""
        return v

    class Config:
        from_attributes = True
        extra = 'allow'  # 允许额外字段

class PaymentUpdate(BaseModel):
    status: Optional[PaymentStatus] = None
    transaction_id: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=200)

class PaymentMethod(str, Enum):
    ALIPAY = "alipay"
    WECHAT = "wechat"
    CREDIT_CARD = "credit_card"

class PaymentRequest(BaseModel):
    member_id: int
    amount: int = Field(..., gt=0)
    type: PaymentType
    method: PaymentMethod
    description: Optional[str] = Field(None, max_length=200)
    return_url: Optional[str] = None
    notify_url: Optional[str] = None

class PaymentResponse(BaseModel):
    payment_id: int
    payment_url: Optional[str] = None
    qr_code: Optional[str] = None
    prepay_id: Optional[str] = None
    status: PaymentStatus

class PaymentCallback(BaseModel):
    transaction_id: str = Field(..., max_length=100)
    payment_id: int
    status: PaymentStatus
    amount: int = Field(..., gt=0)
    sign: str = Field(..., max_length=255)

class PaymentRefund(BaseModel):
    payment_id: int
    amount: int = Field(..., gt=0)
    reason: Optional[str] = Field(None, max_length=200)

class PaymentRefundResponse(BaseModel):
    refund_id: int
    status: str
    refund_amount: int

class EntryRecordBase(BaseModel):
    entry_time: datetime
    exit_time: Optional[datetime] = None

class EntryRecordCreate(EntryRecordBase):
    member_id: int

class EntryRecord(EntryRecordBase):
    id: int
    member_id: int
    created_at: datetime

    @validator('*', pre=True)
    def validate_dynamic_fields(cls, v):
        """支持动态字段的序列化"""
        return v

    class Config:
        from_attributes = True
        extra = 'allow'  # 允许额外字段

class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"

class BookingBase(BaseModel):
    status: BookingStatus = BookingStatus.PENDING

class BookingCreate(BookingBase):
    member_id: int
    course_id: int

class BookingUpdate(BaseModel):
    status: Optional[BookingStatus] = None

class Booking(BookingBase):
    id: int
    member_id: int
    course_id: int
    created_at: datetime

    @validator('*', pre=True)
    def validate_dynamic_fields(cls, v):
        """支持动态字段的序列化"""
        return v

    class Config:
        from_attributes = True
        extra = 'allow'  # 允许额外字段

class MemberWithRelations(Member):
    status_logs: List[MemberStatusLog] = []
    entry_records: List[EntryRecord] = []
    payments: List[Payment] = []
    bookings: List[Booking] = []

    class Config:
        from_attributes = True

class CourseWithRelations(Course):
    bookings: List[Booking] = []

    class Config:
        from_attributes = True
