from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    instructor = Column(String, nullable=False)
    schedule = Column(DateTime, nullable=False)
    max_participants = Column(Integer, nullable=False)

    bookings = relationship("Booking", back_populates="course")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, nullable=False)

    course = relationship("Course", back_populates="bookings")
    user = relationship("User", back_populates="bookings")