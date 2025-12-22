from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from .core.config import settings, database_config

# Create async engine with connection pool settings
engine = create_async_engine(
    database_config["url"].replace("sqlite://", "sqlite+aiosqlite://"),
    pool_size=database_config["pool_size"],
    max_overflow=database_config["max_overflow"],
    pool_timeout=database_config["pool_timeout"],
    pool_recycle=database_config["pool_recycle"],
    echo=database_config["echo"]
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create declarative base for models
Base = declarative_base()

# Dependency to get DB session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Initialize database
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
