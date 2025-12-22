from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from pydantic import validator
from pydantic import Field


class CoachBase(BaseModel):
    avatar: Optional[str] = Field(None, description="教练头像URL")
    description: Optional[str] = Field(None, description="教练描述信息")
    name: str
    specialty: str


class CoachCreate(CoachBase):
    pass


class Coach(CoachBase):
    id: int

    class Config:
        orm_mode = True


class CoachScheduleBase(BaseModel):
    max_capacity: int = Field(default=1, description="最大预约人数")
    location: str = Field(..., description="排班地点")
    @validator('end_time')
    def validate_time_range(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v
    status: str = Field(default="available", description="排班状态: available/booked/cancelled")
    coach_id: int = Field(..., description="关联教练ID")
    start_time: datetime = Field(..., description="排班开始时间")
    end_time: datetime = Field(..., description="排班结束时间")
    course_id: Optional[int] = Field(None, description="关联课程ID，可为空")


class CoachScheduleCreate(CoachScheduleBase):
    pass


class CoachSchedule(CoachScheduleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class CoachScheduleUpdate(BaseModel):
    max_capacity: Optional[int] = Field(None, description="更新最大预约人数")
    location: Optional[str] = Field(None, description="更新排班地点")
    start_time: Optional[datetime] = Field(None, description="更新排班开始时间")
    end_time: Optional[datetime] = Field(None, description="更新排班结束时间")
    course_id: Optional[int] = Field(None, description="更新关联课程ID")
    status: Optional[str] = Field(None, description="更新排班状态: available/booked/cancelled")
    
    @validator('end_time')
    def validate_time_range(cls, v, values):
        if 'start_time' in values and v and values['start_time'] and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v
        
    class Config:
        orm_mode = True
