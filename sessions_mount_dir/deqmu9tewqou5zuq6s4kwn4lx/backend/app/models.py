from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Index, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    bookings = relationship("Booking", back_populates="user")
    
    __table_args__ = (
        Index('idx_user_active_created', 'is_active', 'created_at'),
    )

class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(String(500))
    instructor = Column(String(100), nullable=False)
    max_capacity = Column(Integer, nullable=False)
    current_bookings = Column(Integer, default=0, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    version = Column(Integer, default=1, nullable=False)  # For optimistic concurrency control
    
    # Relationships
    bookings = relationship("Booking", back_populates="course")
    
    __table_args__ = (
        CheckConstraint('current_bookings >= 0', name='check_current_bookings_non_negative'),
        CheckConstraint('current_bookings <= max_capacity', name='check_current_bookings_within_capacity'),
        CheckConstraint('max_capacity > 0', name='check_max_capacity_positive'),
        Index('idx_course_time_active', 'start_time', 'is_active'),
        Index('idx_course_instructor_time', 'instructor', 'start_time'),
        Index('idx_course_version', 'version'),  # For concurrency control
    )

class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    booking_time = Column(DateTime(timezone=True), server_default=func.now())
    is_cancelled = Column(Boolean, default=False, index=True)
    cancelled_at = Column(DateTime(timezone=True))
    version = Column(Integer, default=1, nullable=False)  # For optimistic concurrency control
    
    # Relationships
    user = relationship("User", back_populates="bookings")
    course = relationship("Course", back_populates="bookings")
    
    __table_args__ = (
        Index('idx_booking_user_course', 'user_id', 'course_id', unique=True),
        Index('idx_booking_time_cancelled', 'booking_time', 'is_cancelled'),
        Index('idx_booking_version', 'version'),  # For concurrency control
    )