from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from .core.config import settings
from .core.database import init_db
from .core.logging import setup_logging
from .core.rate_limit import RateLimitMiddleware
from .routers import course


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    init_db()
    setup_logging()
    yield
    # 关闭时清理资源
    logging.getLogger(__name__).info("Application shutting down")


# 创建FastAPI应用实例
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="健身房课程预约系统",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加受信任主机中间件
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# 添加速率限制中间件
app.add_middleware(RateLimitMiddleware)

# 包含路由
app.include_router(course.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Welcome to Gym Course Booking System API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger = logging.getLogger(__name__)
    logger.error(f"Global exception handler: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
