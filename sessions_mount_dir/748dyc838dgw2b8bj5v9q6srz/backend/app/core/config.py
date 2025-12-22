from pydantic import BaseSettings, Field
from typing import Optional
import os

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "Membership System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Database settings
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    
    # Redis settings
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    
    # Redis connection pool settings
    REDIS_MAX_CONNECTIONS: int = Field(default=20, env="REDIS_MAX_CONNECTIONS")
    REDIS_MIN_CONNECTIONS: int = Field(default=5, env="REDIS_MIN_CONNECTIONS")
    REDIS_CONNECTION_TIMEOUT: int = Field(default=5, env="REDIS_CONNECTION_TIMEOUT")
    REDIS_SOCKET_TIMEOUT: int = Field(default=5, env="REDIS_SOCKET_TIMEOUT")
    REDIS_SOCKET_CONNECT_TIMEOUT: int = Field(default=5, env="REDIS_SOCKET_CONNECT_TIMEOUT")
    
    # Redis performance settings
    REDIS_MAX_IDLE_TIME: int = Field(default=300, env="REDIS_MAX_IDLE_TIME")
    REDIS_IDLE_CHECK_INTERVAL: int = Field(default=30, env="REDIS_IDLE_CHECK_INTERVAL")
    REDIS_RETRY_ON_TIMEOUT: bool = Field(default=True, env="REDIS_RETRY_ON_TIMEOUT")
    REDIS_HEALTH_CHECK_INTERVAL: int = Field(default=30, env="REDIS_HEALTH_CHECK_INTERVAL")
    
    # Cache settings
    CACHE_TTL: int = Field(default=3600, env="CACHE_TTL")  # 1 hour default
    CACHE_PREFIX: str = Field(default="membership:", env="CACHE_PREFIX")
    
    # Queue settings
    QUEUE_NAME: str = Field(default="membership_queue", env="QUEUE_NAME")
    QUEUE_MAX_RETRIES: int = Field(default=3, env="QUEUE_MAX_RETRIES")
    
    # Security settings
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Payment settings
    PAYMENT_WEBHOOK_SECRET: Optional[str] = Field(default=None, env="PAYMENT_WEBHOOK_SECRET")
    PAYMENT_TIMEOUT: int = Field(default=300, env="PAYMENT_TIMEOUT")  # 5 minutes
    
    # Notification settings
    NOTIFICATION_RETRY_ATTEMPTS: int = Field(default=3, env="NOTIFICATION_RETRY_ATTEMPTS")
    NOTIFICATION_RETRY_DELAY: int = Field(default=60, env="NOTIFICATION_RETRY_DELAY")  # seconds
    
    # Monitoring settings
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    METRICS_PORT: int = Field(default=9090, env="METRICS_PORT")
    
    # Tracing settings
    JAEGER_ENDPOINT: Optional[str] = Field(default=None, env="JAEGER_ENDPOINT")
    JAEGER_SERVICE_NAME: str = Field(default="membership-backend", env="JAEGER_SERVICE_NAME")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def redis_url(self) -> str:
        """Construct Redis URL from settings"""
        auth_part = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth_part}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def redis_connection_kwargs(self) -> dict:
        """Get Redis connection pool configuration"""
        return {
            "max_connections": self.REDIS_MAX_CONNECTIONS,
            "min_connections": self.REDIS_MIN_CONNECTIONS,
            "timeout": self.REDIS_CONNECTION_TIMEOUT,
            "socket_timeout": self.REDIS_SOCKET_TIMEOUT,
            "socket_connect_timeout": self.REDIS_SOCKET_CONNECT_TIMEOUT,
            "max_idle_time": self.REDIS_MAX_IDLE_TIME,
            "idle_check_interval": self.REDIS_IDLE_CHECK_INTERVAL,
            "retry_on_timeout": self.REDIS_RETRY_ON_TIMEOUT,
            "health_check_interval": self.REDIS_HEALTH_CHECK_INTERVAL,
        }

# Global settings instance
settings = Settings()