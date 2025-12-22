from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Generator
from sqlalchemy import LargeBinary

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@db:5432/fitness_db"


# Configure connection pool settings
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    connect_args={"connect_timeout": 5}
)
# Test the database connection
def check_db_connection():
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        print("Database connection successful")
        return True
    except Exception as e:
        print(f"Database connection failed: {str(e)}")
        return False

check_db_connection()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Generator[SessionLocal, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Member(Base):
    payments = relationship("Payment", back_populates="member")
    __tablename__ = "members"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    phone = Column(String(20), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    join_date = Column(DateTime, default=datetime.utcnow)
    
    cards = relationship("MemberCard", back_populates="member")
    bookings = relationship("CourseBooking", back_populates="member")

class MemberCard(Base):
    __tablename__ = "member_cards"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    card_number = Column(String(20), unique=True, index=True)
    expiry_date = Column(DateTime)
    status = Column(String(20), default="active")
    
    member = relationship("Member", back_populates="cards")

class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    duration = Column(Integer)  # in minutes
    capacity = Column(Integer)
    
    schedules = relationship("CourseSchedule", back_populates="course")

class CourseSchedule(Base):
    __tablename__ = "course_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    coach_id = Column(Integer, ForeignKey("coaches.id"))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    
    course = relationship("Course", back_populates="schedules")
    coach = relationship("Coach", back_populates="schedules")
    bookings = relationship("CourseBooking", back_populates="schedule")

class CourseBooking(Base):
    __tablename__ = "course_bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    schedule_id = Column(Integer, ForeignKey("course_schedules.id"))
    booking_time = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="confirmed")
    
    member = relationship("Member", back_populates="bookings")
    schedule = relationship("CourseSchedule", back_populates="bookings")

class Coach(Base):


class CoachAvailability(Base):


class CoachLeave(Base):


class CoachSchedule(Base):
    __tablename__ = "coach_schedules"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"))
    day_of_week = Column(Integer)  # 0-6 for Monday-Sunday
    start_time = Column(String(10))  # e.g. "09:00"
    end_time = Column(String(10))  # e.g. "17:00"
    is_available = Column(Boolean, default=True)

    coach = relationship("Coach")
    __tablename__ = "coach_leaves"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    reason = Column(String(500))
    status = Column(String(20), default="pending")  # pending/approved/rejected

    coach = relationship("Coach", back_populates="leaves")
    __tablename__ = "coach_availabilities"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"))
    date = Column(DateTime)
    is_available = Column(Boolean, default=True)
    reason = Column(String(500), nullable=True)

    coach = relationship("Coach", back_populates="availabilities")
    __tablename__ = "coaches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    phone = Column(String(20), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    specialty = Column(String(100))
    available_days = Column(String(100))  # e.g. "1,2,3" for Mon,Tue,Wed
    unavailable_dates = Column(String(1000))  # JSON string of unavailable dates

    schedules = relationship("CourseSchedule", back_populates="coach")
    availabilities = relationship("CoachAvailability", back_populates="coach")
    leaves = relationship("CoachLeave", back_populates="coach")
    __tablename__ = "coaches"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    phone = Column(String(20), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    specialty = Column(String(100))
    available_days = Column(String(100))  # e.g. "1,2,3" for Mon,Tue,Wed
    unavailable_dates = Column(String(1000))  # JSON string of unavailable dates
    
    schedules = relationship("CourseSchedule", back_populates="coach")


    __tablename__ = "coach_availabilities"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"))
    date = Column(DateTime)
    is_available = Column(Boolean, default=True)
    reason = Column(String(500), nullable=True)

    coach = relationship("Coach")



class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    amount = Column(Integer, nullable=False)  # in cents to avoid floating point issues
    payment_method = Column(String(50), nullable=False)
    transaction_id = Column(String(100), unique=True, index=True)
    encrypted_card_data = Column(LargeBinary)  # encrypted payment card data
    payment_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="completed")  # completed/failed/refunded
    description = Column(String(500))

    member = relationship("Member", back_populates="payments")
    __tablename__ = "coach_leaves"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    reason = Column(String(500))
    status = Column(String(20), default="pending")  # pending/approved/rejected

    coach = relationship("Coach")
    __tablename__ = "coach_schedules"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"))
    day_of_week = Column(Integer)  # 0-6 for Monday-Sunday
    start_time = Column(String(10))  # e.g. "09:00"
    end_time = Column(String(10))  # e.g. "17:00"
    is_available = Column(Boolean, default=True)

    coach = relationship("Coach")

# Create all tables
def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()