from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from typing import Generator

from app.core.config import settings, DATABASE_CONFIG

# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=DATABASE_CONFIG["pool_size"],
    max_overflow=DATABASE_CONFIG["max_overflow"],
    pool_timeout=DATABASE_CONFIG["pool_timeout"],
    pool_recycle=DATABASE_CONFIG["pool_recycle"],
    echo=DATABASE_CONFIG["echo"]
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话
    
    Returns:
        Generator[Session, None, None]: 数据库会话生成器
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    初始化数据库
    创建所有表
    """
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """
    删除数据库
    删除所有表
    """
    Base.metadata.drop_all(bind=engine)
