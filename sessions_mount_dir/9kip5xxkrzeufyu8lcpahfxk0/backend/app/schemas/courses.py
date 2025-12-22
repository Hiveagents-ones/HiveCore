from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class CourseBase(BaseModel):
    name: str
    description: Optional[str] = None
    duration: int  # in minutes
    capacity: int


class CourseCreate(CourseBase):
    pass


class Course(CourseBase):
    id: int

    class Config:
        orm_mode = True


class CourseScheduleBase(BaseModel):
    course_id: int
    coach_id: int
    start_time: datetime
    end_time: datetime


class CourseScheduleCreate(CourseScheduleBase):
    pass


class CourseSchedule(CourseScheduleBase):
    id: int
    available_slots: int

    class Config:
        orm_mode = True


class CourseBookingBase(BaseModel):
    member_id: int
    schedule_id: int


class CourseBookingCreate(CourseBookingBase):
    pass


class CourseBooking(CourseBookingBase):
    id: int
    booking_time: datetime
    status: str  # e.g. 'confirmed', 'cancelled'

    class Config:
        orm_mode = True


class CourseWithSchedules(Course):
    schedules: List[CourseSchedule] = []


class ScheduleWithBookings(CourseSchedule):
    bookings: List[CourseBooking] = []