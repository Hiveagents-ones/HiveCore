from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any

class CourseBase(BaseModel):
    title: str = Field(..., max_length=100, description="课程标题")
    description: Optional[str] = Field(None, description="课程描述")
    instructor: str = Field(..., max_length=100, description="授课教练")
    capacity: int = Field(..., gt=0, description="课程容量")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    location: str = Field(..., max_length=100, description="上课地点")
    is_active: bool = Field(True, description="是否激活")
    schedule_type: str = Field(..., max_length=50, description="排课类型")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="自定义字段")

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
    schedule_type: Optional[str] = Field(None, max_length=50)
    custom_fields: Optional[Dict[str, Any]] = None

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


class ScheduleBase(BaseModel):
    course_id: int = Field(..., description="课程ID")
    instructor: str = Field(..., max_length=100, description="授课教练")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    location: str = Field(..., max_length=100, description="上课地点")
    capacity: int = Field(..., gt=0, description="课程容量")
    is_active: bool = Field(True, description="是否激活")
    recurring_pattern: Optional[str] = Field(None, description="重复模式")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="自定义字段")

class ScheduleCreate(ScheduleBase):
    pass

class ScheduleUpdate(BaseModel):
    instructor: Optional[str] = Field(None, max_length=100)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=100)
    capacity: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None
    recurring_pattern: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None

class ScheduleInDB(ScheduleBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Schedule(ScheduleInDB):
    pass

class CourseWithSchedules(Course):
    schedules: list[Schedule] = Field(default_factory=list, description="排课列表")