from sqlalchemy import create_engine, Column, Integer, String, Date, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Boolean
from typing import Generator
from datetime import timedelta
import redis

SQLALCHEMY_DATABASE_URL = "sqlite:///./gym.db"
REDIS_URL = "redis://localhost:6379"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Generator:
    """
    Get SQLAlchemy database session
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
    phone = Column(String(20), unique=True, index=True)
    email = Column(String(50), unique=True, index=True)
    join_date = Column(Date, nullable=False)
    
    payments = relationship("Payment", back_populates="member")
    
class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    schedule = Column(String(100), nullable=False)
    coach_id = Column(Integer, ForeignKey("coaches.id"))
    max_members = Column(Integer, nullable=False)
    
    coach = relationship("CoachSchedule", back_populates="courses")
    
class CoachSchedule(Base):
    __tablename__ = "coaches"
    
    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(String(20), default="available")
    
    courses = relationship("Course", back_populates="coach")
    
class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    amount = Column(Float, nullable=False)
    payment_date = Column(Date, nullable=False)
    payment_method = Column(String(20), nullable=False)
    
    member = relationship("Member", back_populates="payments")

Base.metadata.create_all(bind=engine)

# Redis connection pool
redis_pool = redis.ConnectionPool.from_url(REDIS_URL, decode_responses=True)

# Redis cache settings
CACHE_EXPIRE_SECONDS = 3600  # 1 hour

class RedisCache:
    """
    Redis cache wrapper with expiration support
    """
    def __init__(self):
        self.redis = redis.Redis(connection_pool=redis_pool)

    def get(self, key: str) -> str:
        """Get cached value by key"""
        return self.redis.get(key)

    def set(self, key: str, value: str, expire: int = CACHE_EXPIRE_SECONDS) -> bool:
        """Set cached value with expiration"""
        return self.redis.setex(key, timedelta(seconds=expire), value)

    def delete(self, key: str) -> bool:
        """Delete cached value"""
        return self.redis.delete(key)


def get_redis() -> redis.Redis:
    """
    Get Redis connection from pool
    """
    return redis.Redis(connection_pool=redis_pool)


def get_redis_cache() -> RedisCache:
    """
    Get Redis cache instance
    """
    return RedisCache()