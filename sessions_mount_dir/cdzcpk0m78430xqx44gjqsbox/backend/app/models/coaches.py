from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy import Boolean
from sqlalchemy.orm import relationship
from .database import Base


class Coach(Base):
    __tablename__ = 'coaches'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    specialty = Column(String)
    contact = Column(String, unique=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    schedules = relationship("Schedule", back_populates="coach")
    courses = relationship("Course", back_populates="coach")


class Schedule(Base):
    __tablename__ = 'schedules'

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey('coaches.id'))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=True)
    
    coach = relationship("Coach", back_populates="schedules")
    course = relationship("Course", back_populates="schedule")

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
class Schedule(Base):
    __tablename__ = 'schedules'

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey('coaches.id'))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=True)
    is_booked = Column(Boolean, default=False, nullable=False)

    coach = relationship("Coach", back_populates="schedules")
    course = relationship("Course", back_populates="schedule")