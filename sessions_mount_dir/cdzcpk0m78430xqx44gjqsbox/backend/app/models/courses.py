from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class Course(Base):
    __tablename__ = 'courses'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    schedule = Column(DateTime, nullable=False)
    duration = Column(Integer, nullable=False)  # in minutes
    max_capacity = Column(Integer, nullable=False, default=20)
    current_bookings = Column(Integer, nullable=False, default=0)
    coach_id = Column(Integer, ForeignKey('coaches.id'))

    coach = relationship("Coach", back_populates="courses")
    bookings = relationship("Booking", back_populates="course")


class Booking(Base):
    __tablename__ = 'bookings'

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey('members.id'))
    course_id = Column(Integer, ForeignKey('courses.id'))
    booking_time = Column(DateTime, nullable=False)
    status = Column(String, default='confirmed')  # confirmed/cancelled

    member = relationship("Member", back_populates="bookings")
    course = relationship("Course", back_populates="bookings")


class Coach(Base):
    __tablename__ = 'coaches'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    specialty = Column(String)
    contact = Column(String)

    courses = relationship("Course", back_populates="coach")
    schedules = relationship("Schedule", back_populates="coach")


class Schedule(Base):
    __tablename__ = 'schedules'

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey('coaches.id'))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=True)

    coach = relationship("Coach", back_populates="schedules")
    course = relationship("Course")
