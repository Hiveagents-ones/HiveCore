from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from pydantic import Field


class CourseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="课程名称")
    schedule: datetime = Field(..., description="课程时间")
    duration: int = Field(..., gt=0, le=240, description="课程时长(分钟)")
    coach_id: int = Field(..., gt=0, description="教练ID")


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="课程名称")
    schedule: Optional[datetime] = Field(None, description="课程时间")
    duration: Optional[int] = Field(None, gt=0, le=240, description="课程时长(分钟)")
    coach_id: Optional[int] = Field(None, gt=0, description="教练ID")


class Course(CourseBase):
    id: int

    class Config:
        orm_mode = True


class BookingBase(BaseModel):
    member_id: int = Field(..., gt=0, description="会员ID")
    course_id: int = Field(..., gt=0, description="课程ID")
    status: str = Field(..., regex="^(pending|confirmed|cancelled)$", description="预约状态")


class BookingCreate(BookingBase):
    pass


class Booking(BookingBase):
    id: int
    booking_time: datetime

    class Config:
        orm_mode = True


class CourseWithBookings(Course):
    bookings: list[Booking] = []

    class Config:
        orm_mode = True