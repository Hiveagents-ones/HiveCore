from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from typing import Generator
import logging
from .config import settings

logger = logging.getLogger(__name__)

# Create database engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=StaticPool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Dependency to get DB session
def get_db() -> Generator:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize database
def init_db() -> None:
    """Initialize database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

# Query optimizer helper
class QueryOptimizer:
    """Helper class for query optimization"""
    
    @staticmethod
    def optimize_query(query, limit: int = 100, offset: int = 0):
        """Apply common query optimizations"""
        return query.limit(limit).offset(offset)
    
    @staticmethod
    def with_pagination(query, page: int = 1, per_page: int = 10):
        """Apply pagination to query"""
        offset = (page - 1) * per_page
        return query.limit(per_page).offset(offset)
    
    @staticmethod
    def count_total(query):
        """Get total count of records"""
        return query.count()

# Database health check
def check_db_health() -> bool:
    """Check database connection health"""
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False