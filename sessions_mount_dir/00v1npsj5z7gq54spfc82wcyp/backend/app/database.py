from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Date, Float, DateTime

# Database connection URL - adjust according to your PostgreSQL configuration
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@localhost/fitness_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Dependency function to get DB session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Data Models
class Member(Base):
    """Member model for fitness club members"""
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, index=True)
    join_date = Column(Date, nullable=False)
    membership_type = Column(String(50), nullable=False)

class Course(Base):
    """Course model for fitness courses"""
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    coach_id = Column(Integer, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

class Coach(Base):
    """Coach model for fitness coaches"""
    __tablename__ = "coaches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    specialty = Column(String(100), nullable=False)

class Payment(Base):
    """Payment model for member payments"""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    payment_date = Column(Date, nullable=False)
    payment_type = Column(String(50), nullable=False)

# Create all tables
Base.metadata.create_all(bind=engine)