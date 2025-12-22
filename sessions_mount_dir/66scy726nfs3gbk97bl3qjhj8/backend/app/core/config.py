import os
from typing import Optional
from pydantic import BaseSettings

class Settings(BaseSettings):
    # 应用基础配置
    APP_NAME: str = "会员信息管理系统"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 数据库配置
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://username:password@localhost:5432/member_management"
    )
    
    # 安全配置
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "your-secret-key-here-change-in-production"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 加密配置
    ENCRYPTION_KEY: str = os.getenv(
        "ENCRYPTION_KEY",
        "your-encryption-key-here-32-chars-long"
    )
    
    # CORS配置
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://nEywWCST.hivecore.local"
    ]
    
    # API配置
    API_V1_STR: str = "/api/v1"
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"
    
    # 分页配置
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # 文件上传配置
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 创建全局配置实例
settings = Settings()

# 数据库配置常量
DATABASE_CONFIG = {
    "pool_size": 10,
    "max_overflow": 20,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "echo": settings.DEBUG
}

# 敏感字段加密配置
ENCRYPTED_FIELDS = [
    "id_card_number",
    "phone_number",
    "health_status"
]

# 会员信息字段配置
MEMBER_FIELDS = {
    "name": {"type": "string", "required": True, "max_length": 50},
    "phone_number": {"type": "string", "required": True, "max_length": 20},
    "id_card_number": {"type": "string", "required": True, "max_length": 18},
    "health_status": {"type": "string", "required": False, "max_length": 500},
    "address": {"type": "string", "required": False, "max_length": 200},
    "email": {"type": "string", "required": False, "max_length": 100},
    "registration_date": {"type": "datetime", "required": True},
    "last_updated": {"type": "datetime", "required": True}
}

# API响应配置
RESPONSE_CONFIG = {
    "success_code": 200,
    "error_code": 400,
    "not_found_code": 404,
    "unauthorized_code": 401,
    "forbidden_code": 403,
    "server_error_code": 500
}

# 缓存配置
CACHE_CONFIG = {
    "default_timeout": 300,
    "key_prefix": "member_management:",
    "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/0")
}

# 任务队列配置
CELERY_CONFIG = {
    "broker_url": os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    "result_backend": os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
    "task_serializer": "json",
    "accept_content": ["json"],
    "result_serializer": "json",
    "timezone": "UTC",
    "enable_utc": True
}