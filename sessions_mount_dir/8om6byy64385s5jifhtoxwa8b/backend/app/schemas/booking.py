from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from ..models.booking import BookingStatus

class BookingBase(BaseModel):
    user_id: int
    class_schedule_id: int
    status: Optional[BookingStatus] = BookingStatus.PENDING

class BookingCreate(BookingBase):
    pass

class BookingUpdate(BaseModel):
    status: Optional[BookingStatus] = None

class BookingInDBBase(BookingBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Booking(BookingInDBBase):
    pass

class BookingWithDetails(BookingInDBBase):
    user: Optional[dict] = None
    class_schedule: Optional[dict] = None