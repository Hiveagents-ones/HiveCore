from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from typing import Generator

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@db/fitness_db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, pool_recycle=3600, pool_size=20, max_overflow=0
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Dependency


Base = declarative_base()

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    phone = Column(String(20), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    card_status = Column(String(20), default="active")
    join_date = Column(DateTime, nullable=False)
    address = Column(String(200))
    emergency_contact = Column(String(50))
    bookings = relationship("Booking", back_populates="member")

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    schedule = Column(DateTime)
    duration = Column(Integer)
    coach_id = Column(Integer, ForeignKey("coaches.id"))
    coach = relationship("Coach", back_populates="courses")

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    booking_time = Column(DateTime)
    status = Column(String(20), default="confirmed")
    payment_status = Column(String(20), default="unpaid")
    member = relationship("Member", back_populates="bookings")
    course = relationship("Course")

class Coach(Base):
    __tablename__ = "coaches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    specialty = Column(String(100))
    contact = Column(String(50))
    courses = relationship("Course", back_populates="coach")

class Schedule(Base):
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    amount = Column(Integer, nullable=False)
    payment_date = Column(DateTime, nullable=False)
    payment_method = Column(String(50))
    status = Column(String(20), default="completed")
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    course_id = Column(Integer, ForeignKey("courses.id"))

Base.metadata.create_all(bind=engine)