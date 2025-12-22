from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base

class CoachSchedule(Base):
    """教练排班数据模型"""
    __tablename__ = "coach_schedules"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(Enum("available", "booked", "cancelled", "maintenance", name="schedule_status"), default="available")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(String(255), nullable=True)

    coach = relationship("Coach", back_populates="schedules")

class Coach(Base):
    """教练基本信息模型"""
    __tablename__ = "coaches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(100), nullable=False)
    specialty = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    schedules = relationship("CoachSchedule", back_populates="coach")
    courses = relationship("Course", back_populates="coach")