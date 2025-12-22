from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base


class Reservation(Base):
    __tablename__ = 'reservations'

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey('members.id'))
    course_id = Column(Integer, ForeignKey('courses.id'))
    status = Column(String, default='pending')  # pending/confirmed/cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    member = relationship("Member", back_populates="reservations")
    course = relationship("Course", back_populates="reservations")

    def __repr__(self):
        return f"<Reservation(id={self.id}, member_id={self.member_id}, course_id={self.course_id})>"