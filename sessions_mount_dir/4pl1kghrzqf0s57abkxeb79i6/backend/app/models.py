from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Float
from sqlalchemy.orm import relationship
from .database import Base
import enum
from datetime import datetime

class GenderEnum(enum.Enum):
    male = "male"
    female = "female"
    other = "other"

class MembershipStatusEnum(enum.Enum):
    active = "active"
    frozen = "frozen"
    expired = "expired"

class MembershipTypeEnum(enum.Enum):
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"

class BookingStatusEnum(enum.Enum):
    booked = "booked"
    cancelled = "cancelled"
    completed = "completed"

class PaymentTypeEnum(enum.Enum):
    membership = "membership"
    course = "course"
    personal_training = "personal_training"
    other = "other"

class PaymentMethodEnum(enum.Enum):
    cash = "cash"
    card = "card"
    online = "online"

class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    gender = Column(Enum(GenderEnum), nullable=False)
    age = Column(Integer, nullable=False)
    phone = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=True)
    membership_type = Column(Enum(MembershipTypeEnum), nullable=False)
    membership_status = Column(Enum(MembershipStatusEnum), default=MembershipStatusEnum.active)
    membership_start = Column(DateTime, default=datetime.utcnow)
    membership_end = Column(DateTime, nullable=True)
    fitness_goal = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bookings = relationship("Booking", back_populates="member")
    payments = relationship("Payment", back_populates="member")
    access_records = relationship("AccessRecord", back_populates="member")

class MemberCard(Base):
    __tablename__ = "member_cards"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    card_number = Column(String, unique=True, nullable=False)
    card_type = Column(Enum(MembershipTypeEnum), nullable=False)
    status = Column(Enum(MembershipStatusEnum), default=MembershipStatusEnum.active)
    issue_date = Column(DateTime, default=datetime.utcnow)
    expiry_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    member = relationship("Member", back_populates="member_card")

class AccessRecord(Base):
    __tablename__ = "access_records"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    access_time = Column(DateTime, default=datetime.utcnow)
    access_type = Column(String, nullable=False)  # 'entry' or 'exit'
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    member = relationship("Member", back_populates="access_records")

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    description = Column(String, nullable=True)
    duration = Column(Integer, nullable=False)  # in minutes
    max_participants = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    schedules = relationship("CoachSchedule", back_populates="course")
    bookings = relationship("Booking", back_populates="course")

class Coach(Base):
    __tablename__ = "coaches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    gender = Column(Enum(GenderEnum), nullable=False)
    age = Column(Integer, nullable=False)
    phone = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=True)
    specialization = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    schedules = relationship("CoachSchedule", back_populates="coach")

class CoachSchedule(Base):
    __tablename__ = "coach_schedules"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    coach = relationship("Coach", back_populates="schedules")
    course = relationship("Course", back_populates="schedules")

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    status = Column(Enum(BookingStatusEnum), default=BookingStatusEnum.booked)
    booked_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    member = relationship("Member", back_populates="bookings")
    course = relationship("Course", back_populates="bookings")

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    type = Column(Enum(PaymentTypeEnum), nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(Enum(PaymentMethodEnum), nullable=False)
    payment_time = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    member = relationship("Member", back_populates="payments")
