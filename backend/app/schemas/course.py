from datetime import datetime
from pydantic import BaseModel


class CourseBase(BaseModel):
    title: str
    description: str
    instructor: str
    schedule: datetime
    max_participants: int


class CourseCreate(CourseBase):
    pass


class Course(CourseBase):
    id: int

    class Config:
        orm_mode = True


class BookingBase(BaseModel):
    user_id: int
    course_id: int
    status: str = "pending"
    created_at: datetime


class BookingCreate(BookingBase):
    pass


class Booking(BookingBase):
    id: int

    class Config:
        orm_mode = True