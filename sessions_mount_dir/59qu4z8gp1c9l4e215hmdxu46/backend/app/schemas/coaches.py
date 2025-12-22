from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CoachBase(BaseModel):
    name: str
    phone: str
    email: str
    specialization: Optional[str] = None
    hire_date: datetime
    status: str


class CoachCreate(CoachBase):
    pass


class CoachUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    specialization: Optional[str] = None
    status: Optional[str] = None


class Coach(CoachBase):
    id: int

    class Config:
        orm_mode = True



class CoachScheduleBase(BaseModel):
    coach_id: int
    start_time: datetime
    end_time: datetime
    status: str


class CoachScheduleCreate(CoachScheduleBase):
    pass


class CoachScheduleUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None


class CoachSchedule(CoachScheduleBase):
    id: int

    class Config:
        orm_mode = True



class CoachAvailability(BaseModel):
    coach_id: int
    available_start: datetime
    available_end: datetime
    status: str


class CoachAvailabilityCreate(CoachAvailability):
    pass


class CoachAvailabilityUpdate(BaseModel):
    available_start: Optional[datetime] = None
    available_end: Optional[datetime] = None
    status: Optional[str] = None


class CoachAvailabilityResponse(CoachAvailability):
class CoachWithSchedules(CoachBase):
    id: int
    schedules: list[CoachScheduleResponse] = []
    availabilities: list[CoachAvailabilityResponse] = []

    class Config:
        orm_mode = True
    id: int

    class Config:
        orm_mode = True


class CoachScheduleResponse(CoachScheduleBase):
    id: int
    coach_name: str

    class Config:
        orm_mode = True

class CoachAvailabilityResponse(CoachAvailability):
    id: int

    class Config:
        orm_mode = True


class CoachScheduleRequest(BaseModel):
    start_time: datetime
    end_time: datetime
    status: str

    class Config:
        orm_mode = True


class CoachScheduleBulkCreate(BaseModel):
    coach_id: int
    schedules: list[CoachScheduleRequest]


class CoachScheduleBulkUpdate(BaseModel):
    schedules: list[CoachScheduleRequest]


class CoachAvailabilityRequest(BaseModel):
    available_start: datetime
    available_end: datetime
    status: str

    class Config:
        orm_mode = True


class CoachAvailabilityBulkCreate(BaseModel):
    coach_id: int
    availabilities: list[CoachAvailabilityRequest]


class CoachAvailabilityBulkUpdate(BaseModel):
    availabilities: list[CoachAvailabilityRequest]


class CoachScheduleConflictCheck(BaseModel):
class CoachScheduleBulkResponse(BaseModel):
    success: list[CoachScheduleResponse]
    failed: list[dict]

    class Config:
        orm_mode = True


class CoachAvailabilityBulkResponse(BaseModel):
    success: list[CoachAvailabilityResponse]
    failed: list[dict]

    class Config:
        orm_mode = True
    coach_id: int
    start_time: datetime
    end_time: datetime


class CoachAvailabilityConflictCheck(BaseModel):
    coach_id: int
    available_start: datetime
    available_end: datetime
    id: int
    schedules: list[CoachScheduleResponse] = []

    class Config:
        orm_mode = True





