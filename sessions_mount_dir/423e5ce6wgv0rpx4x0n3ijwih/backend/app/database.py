from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 数据库连接URL
# 从环境变量获取，默认使用SQLite
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./gym_management.db"
)

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建Base类，用于声明模型
Base = declarative_base()


# 依赖注入：获取数据库会话
backend_db_import: from .database import engine, Base, get_db
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
