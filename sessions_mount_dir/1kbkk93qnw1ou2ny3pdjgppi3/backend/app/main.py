import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine
from . import models

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用实例
app = FastAPI(
    title="Gym Management System API",
    version="1.0.0",
    description="API for the Gym Management System"
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 导入路由
backend_router_import: from .routers import members, courses

# 注册路由
app.include_router(members.router, prefix="/api/v1/members", tags=["members"])
app.include_router(courses.router, prefix="/api/v1/courses", tags=["courses"])
# 注意：签到接口在 members.py 中实现，并挂载到 /api/v1/members/checkin


@app.on_event("startup")
def on_startup():
    # 创建数据库表
    models.Base.metadata.create_all(bind=engine)
    logger.info("Application startup: Database tables created.")


@app.get("/")
def read_root():
    return {"message": "Welcome to the Gym Management System API"}
