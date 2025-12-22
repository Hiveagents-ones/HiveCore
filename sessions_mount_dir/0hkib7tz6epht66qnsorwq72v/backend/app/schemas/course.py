from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class CourseBase(BaseModel):
    title: str = Field(..., max_length=100, description="课程标题")
    description: Optional[str] = Field(None, description="课程描述")
    instructor: str = Field(..., max_length=100, description="授课教练")
    capacity: int = Field(..., gt=0, description="课程容量")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    location: str = Field(..., max_length=100, description="上课地点")
    is_active: bool = Field(True, description="是否激活")

class CourseCreate(CourseBase):
    pass

class CourseUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
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
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Course(CourseInDB):
    pass

class BookingBase(BaseModel):
    user_id: int = Field(..., description="用户ID")
    course_id: int = Field(..., description="课程ID")

class BookingCreate(BookingBase):
    pass

class BookingUpdate(BaseModel):
    is_cancelled: Optional[bool] = Field(None, description="是否取消")
    cancelled_at: Optional[datetime] = Field(None, description="取消时间")

class BookingInDB(BookingBase):
    id: int
    booked_at: datetime
    is_cancelled: bool
    cancelled_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Booking(BookingInDB):
    pass

class CourseWithBookings(Course):
    bookings: list[Booking] = Field(default_factory=list, description="预约列表")
    current_bookings: int = Field(..., description="当前预约人数")
    available_spots: int = Field(..., description="剩余名额")
