"""Application configuration.

This module contains all configuration settings for the FastAPI application.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings.

    Attributes:
        APP_NAME: Application name
        DEBUG: Debug mode flag
        DATABASE_URL: Async database connection URL
        JWT_SECRET_KEY: Secret key for JWT token signing
        JWT_ALGORITHM: Algorithm for JWT token encoding
        ACCESS_TOKEN_EXPIRE_MINUTES: Default access token expiration time
    """

    # Application
    APP_NAME: str = "Member Management API"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./members.db"

    # JWT Authentication
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings: Application settings
    """
    return Settings()


# Global settings instance
settings = get_settings()
