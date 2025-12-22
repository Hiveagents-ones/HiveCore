from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import members, courses, payments, auth
from .middleware.auth import get_current_user

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建FastAPI应用实例
app = FastAPI(
    title="会员管理系统",
    description="会员信息管理系统API",
    version="1.0.0"
)

# 添加审计中间件
from .middleware.audit import AuditMiddleware
app.add_middleware(AuditMiddleware)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(members.router, prefix="/api/v1/members", tags=["members"])
app.include_router(courses.router, prefix="/api/v1/courses", tags=["courses"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])

# 注册认证路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])


@app.get("/")
async def root():
    return {"message": "会员管理系统API服务正在运行"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
