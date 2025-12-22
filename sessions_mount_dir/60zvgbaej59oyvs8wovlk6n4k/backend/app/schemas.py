from datetime import datetime
from typing import Optional

from typing import Generic, TypeVar, List

from pydantic import BaseModel, Field

from decimal import Decimal

class MemberBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=1, max_length=20)
    card_number: str = Field(..., min_length=1, max_length=50)
    level: str = Field(default='basic', max_length=20)
    remaining_months: int = Field(default=0, ge=0)
    is_active: bool = True

class MemberCreate(MemberBase):
    pass

class MemberUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, min_length=1, max_length=20)
    card_number: Optional[str] = Field(None, min_length=1, max_length=50)
    level: Optional[str] = Field(None, max_length=20)
    remaining_months: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None

class MemberInDB(MemberBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Member(MemberInDB):
    pass

class HistoryBase(BaseModel):
    member_id: int
    action: str = Field(..., max_length=50)
    description: Optional[str] = None

class HistoryCreate(HistoryBase):
    pass

class HistoryInDB(HistoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class History(HistoryInDB):
    pass

class AuditLogBase(BaseModel):
    user_id: int
    action: str = Field(..., max_length=50)
    resource: str = Field(..., max_length=50)
    details: Optional[str] = None
    ip_address: Optional[str] = Field(None, max_length=45)

class AuditLogCreate(AuditLogBase):
    pass

class AuditLogInDB(AuditLogBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class AuditLog(AuditLogInDB):
    pass


class CourseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    instructor: str = Field(..., min_length=1, max_length=100)
    capacity: int = Field(..., gt=0)
    duration_minutes: int = Field(..., gt=0)
    is_active: bool = True

class CourseCreate(CourseBase):
    pass

class CourseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    instructor: Optional[str] = Field(None, min_length=1, max_length=100)
    capacity: Optional[int] = Field(None, gt=0)
    duration_minutes: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None

class CourseInDB(CourseBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Course(CourseInDB):
    pass

class BookingBase(BaseModel):
    member_id: int
    course_id: int
    status: str = Field(default='booked', max_length=20)

class BookingCreate(BookingBase):
    pass

class BookingUpdate(BaseModel):
    status: Optional[str] = Field(None, max_length=20)

class BookingInDB(BookingBase):
    id: int
    booking_time: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Booking(BookingInDB):
    pass


class PaymentBase(BaseModel):
    member_id: int
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    payment_method: str = Field(..., max_length=50)
    status: str = Field(default='pending', max_length=20)
    transaction_id: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    payment_gateway: str = Field(..., max_length=50)
    gateway_transaction_id: Optional[str] = Field(None, max_length=100)
    payment_type: str = Field(default='renewal', max_length=20)  # renewal, course, other
    months: Optional[int] = Field(None, gt=0)  # Number of months for renewal

class PaymentCreate(PaymentBase):
    pass

class PaymentUpdate(BaseModel):
    status: Optional[str] = Field(None, max_length=20)
    transaction_id: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    gateway_transaction_id: Optional[str] = Field(None, max_length=100)
    payment_type: Optional[str] = Field(None, max_length=20)
    months: Optional[int] = Field(None, gt=0)
    refund_amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    refund_reason: Optional[str] = Field(None, max_length=200)

class PaymentInDB(PaymentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Payment(PaymentInDB):
    pass

class NotificationBase(BaseModel):
    member_id: int
    type: str = Field(..., max_length=20)
    title: str = Field(..., max_length=200)
    message: str = Field(..., max_length=1000)
    status: str = Field(default='pending', max_length=20)
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None

class NotificationCreate(NotificationBase):
    pass

class NotificationUpdate(BaseModel):
    status: Optional[str] = Field(None, max_length=20)
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None

class NotificationInDB(NotificationBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Notification(NotificationInDB):
    pass


class PaginationParams(BaseModel):

    page: int = Field(default=1, ge=1)
    size: int = Field(default=10, ge=1, le=100)


T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """通用分页响应模型"""
    items: List[T] = Field(..., description="数据项列表")
    total: int = Field(..., ge=0, description="总记录数")
    page: int = Field(..., ge=1, description="当前页码")
    size: int = Field(..., ge=1, le=100, description="每页大小")
    pages: int = Field(..., ge=0, description="总页数")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "size": 10,
                "pages": 10
            }
        }
    page: int = Field(default=1, ge=1)
    size: int = Field(default=10, ge=1, le=100)


T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """通用分页响应模型"""
    items: List[T] = Field(..., description="数据项列表")
    total: int = Field(..., ge=0, description="总记录数")
    page: int = Field(..., ge=1, description="当前页码")
    size: int = Field(..., ge=1, le=100, description="每页大小")
    pages: int = Field(..., ge=0, description="总页数")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "size": 10,
                "pages": 10
            }
        }
