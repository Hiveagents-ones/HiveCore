from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, Integer, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base


class CoachScheduleBase(BaseModel):
    __tablename__ = "coach_schedules"
    coach_id: int
    start_time: datetime
    end_time: datetime
    available: bool = True


class CoachScheduleCreate(CoachScheduleBase):
    pass


class CoachScheduleUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    available: Optional[bool] = None


class CoachSchedule(CoachScheduleBase):
    id: int

    class Config:
        orm_mode = True


class CoachScheduleLog(BaseModel):
    id: int
    schedule_id: int
    action: str
    changed_at: datetime
    changed_by: int
    old_values: dict
    new_values: dict

    class Config:
        orm_mode = True


class CoachScheduleLogCreate(BaseModel):
    schedule_id: int
    action: str
    changed_by: int
    old_values: dict
    new_values: dict


class CoachScheduleLogDB(Base):
    __tablename__ = "coach_schedule_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, index=True)
    action = Column(String(50))
    changed_at = Column(DateTime, server_default=func.now())
    changed_by = Column(Integer)
    old_values = Column(JSON)
    new_values = Column(JSON)