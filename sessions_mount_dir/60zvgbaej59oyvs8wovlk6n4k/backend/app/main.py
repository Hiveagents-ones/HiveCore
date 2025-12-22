from fastapi import FastAPI, Request, HTTPException
from prometheus_client import make_asgi_app
from prometheus_client import Counter, Histogram, generate_latest
import time
from fastapi import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from .routers import members
from .routers import courses
from .routers import payments
from .routers import auth
from .database import engine, Base
from .routers import notifications
from .routers import membership

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    logger.info("Starting up...")
    # 创建数据库表
    Base.metadata.create_all(bind=engine)
    yield
    # 关闭时执行
    logger.info("Shutting down...")

# 创建FastAPI应用实例
app = FastAPI(
    title="会员信息管理系统",
    description="提供会员信息的增删改查功能",
    version="1.0.0",
    lifespan=lifespan
)

# Define metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)
REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds'
)

# Prometheus metrics app
metrics_app = make_asgi_app()

# Mount metrics app
app.mount("/metrics", metrics_app)

# Metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    REQUEST_DURATION.observe(duration)
    
    return response


# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://n2T3daCJ.hivecore.local"],  # 生产环境应指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理器
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"},
    )

# 包含路由
app.include_router(members.router, prefix="/api/v1/members", tags=["members"])
app.include_router(courses.router, prefix="/api/v1/courses", tags=["courses"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])

app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])

app.include_router(membership.router, prefix="/api/v1/membership", tags=["membership"])

# 根路径
@app.get("/")
async def root():
    return {"message": "会员信息管理系统 API"}

# 健康检查
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "会员信息管理系统"
    }

