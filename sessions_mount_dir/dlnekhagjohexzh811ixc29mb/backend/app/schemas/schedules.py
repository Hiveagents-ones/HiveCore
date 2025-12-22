from datetime import time
from pydantic import BaseModel
from typing import Optional, List


class ScheduleBase(BaseModel):
    coach_id: int
    day_of_week: int
    start_hour: time
    end_hour: time


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    day_of_week: Optional[int] = None
    start_hour: Optional[time] = None
    end_hour: Optional[time] = None


class Schedule(ScheduleBase):
    id: int

    class Config:
        orm_mode = True


class WeeklySchedule(BaseModel):
    coach_id: int
    schedules: List[ScheduleBase]

    class Config:
        orm_mode = True