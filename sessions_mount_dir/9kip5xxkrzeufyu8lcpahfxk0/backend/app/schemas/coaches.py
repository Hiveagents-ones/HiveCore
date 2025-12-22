from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from enum import Enum


class ScheduleStatus(str, Enum):



class CoachBase(BaseModel):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    ON_LEAVE = "on_leave"
    name: str
    phone: str
    email: str
    hire_date: datetime
    specialization: Optional[str] = None


class CoachCreate(CoachBase):
    pass


class CoachUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    specialization: Optional[str] = None


class Coach(CoachBase):
    id: int

    class Config:
        orm_mode = True


class CoachScheduleBase(BaseModel):
    coach_id: int
    start_time: datetime
    end_time: datetime
    status: ScheduleStatus
    course_id: Optional[int] = None
    notes: Optional[str] = None


class CoachScheduleCreate(CoachScheduleBase):
    pass


class CoachScheduleUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[ScheduleStatus] = None
    course_id: Optional[int] = None
    notes: Optional[str] = None


class CoachSchedule(CoachScheduleBase):
    id: int

    class Config:
        orm_mode = True


class CoachWithSchedules(Coach):
    class Config:
        orm_mode = True
    schedules: List[CoachSchedule] = []
class CoachScheduleFilter(BaseModel):
    class Config:
        orm_mode = True
    coach_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[ScheduleStatus] = None
    has_course: Optional[bool] = None


class CoachScheduleBulkCreate(BaseModel):
    coach_id: int
    schedules: List[Dict[str, datetime]]


class CoachLeaveRequest(BaseModel):
    coach_id: int
    start_date: datetime
    end_date: datetime
    reason: str
    status: ScheduleStatus = ScheduleStatus.PENDING


class CoachLeaveResponse(CoachLeaveRequest):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
    class Config:
        orm_mode = True
    coach_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[ScheduleStatus] = None
    has_course: Optional[bool] = None