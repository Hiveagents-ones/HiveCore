from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic import validator
from pydantic import Field


class CourseBase(BaseModel):
    """
    课程基础模型
    Attributes:
        max_capacity: 最大容量
        current_bookings: 当前预约人数
        name: 课程名称
        description: 课程描述
        start_time: 开始时间
        end_time: 结束时间
        booking_deadline: 预约截止时间
        min_booking_hours: 最小预约提前小时数
        version: 乐观锁版本号
    """

    @validator('end_time')
    def validate_end_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v
        
    @validator('max_capacity')
    @validator('booking_deadline')
    def validate_booking_deadline(cls, v, values):
        if v is not None and 'start_time' in values and v >= values['start_time']:
            raise ValueError('booking_deadline must be before start_time')
        return v

    @validator('min_booking_hours')
    def validate_min_booking_hours(cls, v):
        if v < 1:
            raise ValueError('min_booking_hours must be at least 1 hour')
        return v
    def validate_max_capacity(cls, v):
        if v <= 0:
            raise ValueError('max_capacity must be positive')
        return v
    max_capacity: int = 20
    current_bookings: int = 0
    name: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    booking_deadline: Optional[datetime] = None
    min_booking_hours: int = Field(default=2, ge=1, description="至少提前N小时预约")
    version: int = Field(default=0, description="乐观锁版本号")


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    """
    课程更新模型
    Attributes:
        version: 必须提供当前版本号用于乐观锁控制
    """
    max_capacity: Optional[int] = None
    current_bookings: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    version: Optional[int] = Field(description="必须提供当前版本号用于乐观锁控制")


class Course(CourseBase):
    """
    课程响应模型
    Attributes:
        is_bookable: 当前是否可预约
        remaining_slots: 剩余可预约名额
        booking_status: 预约状态
    """
    is_bookable: bool = True
    remaining_slots: int = Field(description="剩余可预约名额")
    booking_status: str = Field(default="open", description="预约状态: open/closed/full")
    
    @validator('is_bookable', 'remaining_slots', 'booking_status', always=True)
    def validate_bookable(cls, v, values):
        if 'current_bookings' in values and 'max_capacity' in values:
            remaining = values['max_capacity'] - values['current_bookings']
            values['remaining_slots'] = remaining
            
            if remaining <= 0:
                values['booking_status'] = 'full'
                return False
            
            if 'start_time' in values and datetime.now() >= values['start_time']:
                values['booking_status'] = 'closed'
                return False
                
            if 'booking_deadline' in values and values['booking_deadline'] is not None \
                    and datetime.now() >= values['booking_deadline']:
                values['booking_status'] = 'closed'
                return False
                
            values['booking_status'] = 'open'
            return True
            
        return False
    id: int

    class Config:
        orm_mode = True