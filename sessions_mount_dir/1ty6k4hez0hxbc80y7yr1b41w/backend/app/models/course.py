from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base


class Course(Base):
    __tablename__ = 'courses'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    schedule = Column(DateTime, nullable=False)
    coach_id = Column(Integer, ForeignKey('coaches.id'))
    max_members = Column(Integer, nullable=False)
    version_uuid = Column(UUID(as_uuid=True), nullable=False, server_default='gen_random_uuid()')
    current_members = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_updated = Column(DateTime, nullable=False, server_default='now()')

    coach = relationship("Coach", back_populates="courses")
    bookings = relationship("Booking", back_populates="course")


class Booking(Base):
    __tablename__ = 'bookings'

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey('members.id'))
    course_id = Column(Integer, ForeignKey('courses.id'))
    booking_time = Column(DateTime, nullable=False)
    version_uuid = Column(UUID(as_uuid=True), nullable=False, server_default='gen_random_uuid()')
    status = Column(String(20), default='confirmed', nullable=False)
    last_updated = Column(DateTime, nullable=False, server_default='now()')

    member = relationship("Member", back_populates="bookings")
    course = relationship("Course", back_populates="bookings")
