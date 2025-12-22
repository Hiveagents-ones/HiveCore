from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@localhost/fitness_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Member(Base):
    __tablename__ = "members"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    membership_type = Column(String)

class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    duration = Column(Integer)  # in minutes
    capacity = Column(Integer)

class Coach(Base):
    __tablename__ = "coaches"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    specialty = Column(String)
    bio = Column(String)

class CourseSchedule(Base):
    __tablename__ = "course_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    coach_id = Column(Integer, ForeignKey("coaches.id"))
    start_time = Column(DateTime)
    end_time = Column(DateTime)

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    amount = Column(Float)
    payment_date = Column(DateTime)
    payment_method = Column(String)

# Create all tables
Base.metadata.create_all(bind=engine)