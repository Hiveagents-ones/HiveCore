from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .database import Base


class Coach(Base):
    __tablename__ = 'coaches'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    specialty = Column(String(100))
    status = Column(Boolean, default=True)
    
    
    # 排班管理相关字段
    work_schedule = Column(JSONB, comment="工作时间安排，JSON格式存储")
    max_courses_per_day = Column(Integer, default=4, comment="每天最多课程数")
    qualifications = Column(String(500), comment="教练资质证书信息")
    working_hours = Column(String(100), comment="工作时间段，格式: HH:MM-HH:MM")
    available_days = Column(String(100), comment="可工作日期，如: 1,2,3,4,5 (1-7表示周一到周日)")
    
    # 关系
    courses = relationship("Course", back_populates="coach")
    leaves = relationship("CoachLeave", back_populates="coach")


class CoachLeave(Base):
    __tablename__ = 'coach_leaves'
    
    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey('coaches.id'))
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    reason = Column(String(200))
    status = Column(String(20), default='pending')  # pending/approved/rejected
    
    # 关系
    coach = relationship("Coach", back_populates="leaves")