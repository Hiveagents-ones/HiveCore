from fastapi import FastAPI
from .database import engine, Base
from .routers import users

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建FastAPI应用实例
app = FastAPI(
    title="用户管理系统",
    description="基于FastAPI的用户注册和登录系统",
    version="1.0.0"
)

# 注册用户路由
app.include_router(users.router)

@app.get("/")
def read_root():
    return {"message": "欢迎使用用户管理系统 API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}