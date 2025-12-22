from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from .database import Base


class Booking(Base):
    """课程预约记录模型"""
    __tablename__ = 'bookings'

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey('members.id'), nullable=False)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    booking_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(20), default='confirmed', nullable=False)  # confirmed/cancelled/completed

    # 定义关系
    member = relationship("Member", back_populates="bookings")
    course = relationship("Course", back_populates="bookings")

    def __repr__(self):
        return f"<Booking(id={self.id}, member_id={self.member_id}, course_id={self.course_id})>"