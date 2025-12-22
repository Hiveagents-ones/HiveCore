from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from sqlalchemy import ForeignKey
from cryptography.fernet import Fernet
from sqlalchemy_utils.types.encrypted.encrypted_type import FernetEngine, StringEncryptedType
from sqlalchemy import LargeBinary

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@localhost/fitness_db?client_encoding=utf8"
SECRET_KEY = Fernet.generate_key()

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
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True)
    phone = Column(StringEncryptedType(String(20), SECRET_KEY, FernetEngine))
    age = Column(Integer)
    gender = Column(String(10))
    address = Column(String(200))
    emergency_contact = Column(StringEncryptedType(String(100), SECRET_KEY, FernetEngine))
    membership_type = Column(String(50))
    membership_expiry = Column(DateTime)
    join_date = Column(DateTime)

class Course(Base):
    
    coach_id = Column(Integer, ForeignKey("coaches.id"))

class Coach(Base):
    __tablename__ = "coaches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True)
    phone = Column(StringEncryptedType(String(20), SECRET_KEY, FernetEngine))
    specialization = Column(String(100))
    hire_date = Column(DateTime)
    certification = Column(String(200))
    years_of_experience = Column(Integer)
    hourly_rate = Column(Float)
    bio = Column(String(1000))
    profile_picture = Column(LargeBinary)
    is_active = Column(Boolean, default=True)

class ScheduleLog(Base):
    __tablename__ = "schedule_logs"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("coach_schedules.id"))
    coach_id = Column(Integer, ForeignKey("coaches.id"))
    action = Column(String(20))  # created, updated, cancelled
    changed_at = Column(DateTime)
    changed_by = Column(Integer, ForeignKey("members.id"))
    old_values = Column(String(1000))
    new_values = Column(String(1000))
    __tablename__ = "coaches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True)
    phone = Column(StringEncryptedType(String(20), SECRET_KEY, FernetEngine))
    specialization = Column(String(100))
    hire_date = Column(DateTime)
    certification = Column(String(200))
    years_of_experience = Column(Integer)
    hourly_rate = Column(Float)
    bio = Column(String(1000))
    profile_picture = Column(LargeBinary)
    is_active = Column(Boolean, default=True)
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    start_time = Column(DateTime)
    end_time = Column(DateTime)

class CoachSchedule(Base):
    
    __tablename__ = "coach_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, nullable=False)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    available = Column(Boolean, default=True)

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    payment_date = Column(DateTime)
    payment_method = Column(StringEncryptedType(String(50), SECRET_KEY, FernetEngine))
    status = Column(String(20), default='pending')
    invoice_number = Column(String(50), unique=True)

# Create all tables
Base.metadata.create_all(bind=engine)

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    coach_id = Column(Integer, ForeignKey("coaches.id"))

# [AUTO-APPENDED] Failed to replace, adding new code:
class CoachSchedule(Base):
    __tablename__ = "coach_schedules"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"), nullable=False)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    available = Column(Boolean, default=True)

# [AUTO-APPENDED] Failed to replace, adding new code:
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_date = Column(DateTime)
    payment_method = Column(StringEncryptedType(String(50), SECRET_KEY, FernetEngine))
    status = Column(String(20), default='pending')
    invoice_number = Column(String(50), unique=True)

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    coach_id = Column(Integer, ForeignKey("coaches.id"))

# [AUTO-APPENDED] Failed to replace, adding new code:
class CoachSchedule(Base):
    __tablename__ = "coach_schedules"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"), nullable=False)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    available = Column(Boolean, default=True)

# [AUTO-APPENDED] Failed to replace, adding new code:
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_date = Column(DateTime)
    payment_method = Column(StringEncryptedType(String(50), SECRET_KEY, FernetEngine))
    status = Column(String(20), default='pending')
    invoice_number = Column(String(50), unique=True)