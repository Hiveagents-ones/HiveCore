from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CourseBase(BaseModel):
    name: str
    description: Optional[str] = None
    duration: int
    capacity: int


class CourseCreate(CourseBase):
    pass


class Course(CourseBase):
    id: int

    class Config:
        orm_mode = True


class CourseScheduleBase(BaseModel):
    course_id: int
    start_time: datetime
    end_time: datetime
    coach_id: int


class CourseScheduleCreate(CourseScheduleBase):
    pass


class CourseSchedule(CourseScheduleBase):
    id: int

    class Config:
        orm_mode = True


class CourseBookingBase(BaseModel):
    member_id: int
    schedule_id: int
    status: str = 'confirmed'


class CourseBookingCreate(CourseBookingBase):
    pass


class CourseBooking(CourseBookingBase):
    id: int
    booking_time: datetime

    class Config:
        orm_mode = True