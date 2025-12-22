from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    instructor = Column(String(100), nullable=False, index=True)
    capacity = Column(Integer, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False)
    location = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_booking_user_course', 'user_id', 'course_id'),
        Index('idx_booking_status', 'is_cancelled', 'booked_at'),
    )
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_course_instructor_time', 'instructor', 'start_time'),
        Index('idx_course_active_time', 'is_active', 'start_time'),
    )
    bookings = relationship("Booking", back_populates="course")

    def __repr__(self):
        return f"<Course(id={self.id}, title='{self.title}', instructor='{self.instructor}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "instructor": self.instructor,
            "capacity": self.capacity,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "location": self.location,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    booked_at = Column(DateTime(timezone=True), server_default=func.now())
    is_cancelled = Column(Boolean, default=False, index=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="bookings")
    course = relationship("Course", back_populates="bookings")

    def __repr__(self):
        return f"<Booking(id={self.id}, user_id={self.user_id}, course_id={self.course_id})>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "course_id": self.course_id,
            "booked_at": self.booked_at.isoformat() if self.booked_at else None,
            "is_cancelled": self.is_cancelled,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None
        }