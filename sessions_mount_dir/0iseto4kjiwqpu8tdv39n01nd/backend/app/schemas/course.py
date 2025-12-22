from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CourseBase(BaseModel):
    name: str = Field(..., max_length=100, description="课程名称")
    description: Optional[str] = Field(None, description="课程描述")
    instructor: str = Field(..., max_length=100, description="教练姓名")
    capacity: int = Field(..., gt=0, description="课程容量")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    location: str = Field(..., max_length=100, description="上课地点")
    is_active: bool = Field(True, description="课程是否激活")


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    instructor: Optional[str] = Field(None, max_length=100)
    capacity: Optional[int] = Field(None, gt=0)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class CourseInDB(CourseBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class Course(CourseInDB):
    current_bookings: int = Field(0, description="当前预约人数")
    available_spots: int = Field(0, description="剩余名额")


class BookingBase(BaseModel):
    course_id: int = Field(..., description="课程ID")


class BookingCreate(BookingBase):
    pass


class BookingUpdate(BaseModel):
    is_cancelled: bool = Field(..., description="是否取消预约")


class BookingInDB(BaseModel):
    id: int
    user_id: int
    course_id: int
    booked_at: datetime
    is_cancelled: bool
    cancelled_at: Optional[datetime]

    class Config:
        from_attributes = True


class Booking(BookingInDB):
    course: Course


class CourseList(BaseModel):
    courses: List[Course]
    total: int


class BookingList(BaseModel):
    bookings: List[Booking]
    total: int
