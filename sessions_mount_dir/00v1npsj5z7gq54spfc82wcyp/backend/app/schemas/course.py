from datetime import datetime
from pydantic import BaseModel, validator
from typing import Optional
from enum import Enum
from backend.app.models.course_type import CourseStatus


class CourseBase(BaseModel):
    course_type_id: int
    name: str
    coach_id: int
    start_time: datetime
    end_time: datetime

    @validator('end_time')
    def validate_time_range(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    course_type_id: Optional[int] = None
    name: Optional[str] = None
    coach_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @validator('end_time')
    def validate_time_range(cls, v, values):
        if 'start_time' in values and v and values['start_time'] and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v


class Course(CourseBase):
    id: int

    class Config:
        orm_mode = True


class CourseBooking(BaseModel):
    member_id: int
    course_id: int


class CourseScheduleQuery(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    coach_id: Optional[int] = None


class CourseTypeBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True
    status: CourseStatus = CourseStatus.ACTIVE
    color_code: str = '#2196F3'
    duration: int
    max_capacity: int
    min_booking_hours: int = 2
    cancellation_hours: int = 1
    allow_booking: bool = True
    booking_window_days: int = 7
    refund_policy: str = 'flexible'
    display_order: int = 0
    price: float = 0.0


class CourseTypeCreate(CourseTypeBase):
    pass


class CourseTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[CourseStatus] = None
    color_code: Optional[str] = None
    duration: Optional[int] = None
    max_capacity: Optional[int] = None
    min_booking_hours: Optional[int] = None
    cancellation_hours: Optional[int] = None
    allow_booking: Optional[bool] = None
    booking_window_days: Optional[int] = None
    refund_policy: Optional[str] = None
    display_order: Optional[int] = None
    price: Optional[float] = None


class CourseType(CourseTypeBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True