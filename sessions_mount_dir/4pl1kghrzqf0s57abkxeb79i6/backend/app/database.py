from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Float
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

# Database URL (PostgreSQL)
SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost/gym_db"

# Create engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Enums
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

# Models
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
    bookings = relationship("Booking", back_populates="schedule")

class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    schedule_id = Column(Integer, ForeignKey("coach_schedules.id"), nullable=False)
    status = Column(Enum(BookingStatusEnum), default=BookingStatusEnum.booked)
    booked_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    member = relationship("Member", back_populates="bookings")
    course = relationship("Course", back_populates="bookings")
    schedule = relationship("CoachSchedule", back_populates="bookings")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    type = Column(Enum(PaymentTypeEnum), nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(Enum(PaymentMethodEnum), nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    member = relationship("Member", back_populates="payments")

# Create all tables
Base.metadata.create_all(bind=engine)
