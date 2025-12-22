from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine, EncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import StringEncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import FernetEngine

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@postgres:5432/fitness_db?application_name=fitness_app&connect_timeout=10"
SECRET_KEY = "your-secret-key-here"  # Should be moved to config in production
FERNET_KEY = "your-fernet-key-here"  # Should be moved to config in production
ENCRYPTION_PAD_LENGTH = 32  # PKCS5 padding length for encrypted fields

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=30,
    connect_args={"options": "-c timezone=utc"},
    echo_pool=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Dependency function that yields db sessions
    Handles session cleanup automatically
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    phone = Column(StringEncryptedType(String(20), SECRET_KEY, FernetEngine, padding='pkcs5', max_length=20+ENCRYPTION_PAD_LENGTH), unique=True, index=True)
    email = Column(StringEncryptedType(String(100), SECRET_KEY, FernetEngine, padding='pkcs5', max_length=100+ENCRYPTION_PAD_LENGTH), unique=True, index=True)
    join_date = Column(DateTime, nullable=False)

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)
    schedule = Column(String(100), nullable=False)
    duration = Column(Integer, nullable=False)

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    booking_time = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="confirmed")

class Coach(Base):
    __tablename__ = "coaches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    phone = Column(StringEncryptedType(String(20), SECRET_KEY, FernetEngine, padding='pkcs5', max_length=20+ENCRYPTION_PAD_LENGTH), unique=True, index=True)
    specialty = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="active")

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_date = Column(DateTime, nullable=False)
    payment_method = Column(String(50), nullable=False)

# Create all tables
Base.metadata.create_all(bind=engine)