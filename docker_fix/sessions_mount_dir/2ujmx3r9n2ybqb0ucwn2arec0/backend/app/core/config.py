from pydantic import BaseSettings, Field
from typing import Optional
import os

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "Gym Membership System"
    DEBUG: bool = Field(default=False, env="DEBUG")
    VERSION: str = "1.0.0"
    
    # Database settings
    DATABASE_URL: str = Field(
        default="sqlite:///./gym.db",
        env="DATABASE_URL"
    )
    
    # Database connection pool settings
    DB_POOL_SIZE: int = Field(default=5, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=10, env="DB_MAX_OVERFLOW")
    DB_POOL_TIMEOUT: int = Field(default=30, env="DB_POOL_TIMEOUT")
    DB_POOL_RECYCLE: int = Field(default=3600, env="DB_POOL_RECYCLE")
    
    # ID generation strategy settings
    ID_STRATEGY: str = Field(default="uuid4", env="ID_STRATEGY")  # Options: uuid4, snowflake, autoincrement
    ID_PREFIX: Optional[str] = Field(default="MBR", env="ID_PREFIX")  # Prefix for member IDs
    
    # Security settings
    SECRET_KEY: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # CORS settings
    CORS_ORIGINS: list = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="CORS_ORIGINS"
    )
    
    # API settings
    API_V1_STR: str = "/api/v1"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create global settings instance
settings = Settings()

# Database configuration dictionary for SQLAlchemy
database_config = {
    "url": settings.DATABASE_URL,
    "pool_size": settings.DB_POOL_SIZE,
    "max_overflow": settings.DB_MAX_OVERFLOW,
    "pool_timeout": settings.DB_POOL_TIMEOUT,
    "pool_recycle": settings.DB_POOL_RECYCLE,
    "echo": settings.DEBUG
}

# ID generation configuration
id_config = {
    "strategy": settings.ID_STRATEGY,
    "prefix": settings.ID_PREFIX
}