from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Response
import datetime
from sqlalchemy.orm import Session
from prometheus_fastapi_instrumentator import Instrumentator

from .routers import members, courses, coaches, payments, invoices, refunds, schedules, payment_methods

from .database import engine, Base, get_db
from .routers.courses import router as courses_router
from .routers.payments import router as payments_router
from .routers.invoices import router as invoices_router
from .routers.refunds import router as refunds_router
from .routers.payment_methods import router as payment_methods_router

app = FastAPI(
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    title="Gym Management System API",
    description="API for managing gym members, courses, coaches and payments",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
# Initialize Prometheus metrics
instrumentator = Instrumentator(
    excluded_handlers=[
        "/api/v1/health",
        "/api/v1/metrics",
        "/"
    ]
)
instrumentator.instrument(app).expose(app, include_in_schema=False)
Base.metadata.create_all(bind=engine)

# Main application entry point

# Include routers
app.include_router(
    schedules.router,
    prefix="/api/v1/schedules",
    tags=["schedules"]
)
app.include_router(
    refunds_router,
    prefix="/api/v1/payments",
    tags=["refunds"]
)
app.include_router(
    invoices_router,
    prefix="/api/v1/invoices",
    tags=["invoices"]
)
app.include_router(
    members.router,
    prefix="/api/v1/members",
    tags=["members"]
)

app.include_router(
    courses_router,
    prefix="/api/v1/courses",
    tags=["courses"]
)

app.include_router(
    coaches.router,
    prefix="/api/v1/coaches",
    tags=["coaches"]
)

app.include_router(
    payments_router,
    prefix="/api/v1/payments",
    tags=["payments"]
)

@app.get("/", include_in_schema=False)
def read_root():
    return Response(content=json.dumps({"message": "Welcome to Gym Management System API"}), media_type="application/json", status_code=200)

@app.get("/api/v1/health", include_in_schema=False)
def health_check(db: Session = Depends(get_db)):
    # 检查数据库连接
    try:
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.get("/api/v1/metrics", include_in_schema=False)
async def metrics():
    return Response(content="", media_type="text/plain", status_code=200)

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
@app.get("/api/v1/health", include_in_schema=False)
def health_check(db: Session = Depends(get_db)):
    # 检查数据库连接
    try:
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"

    return Response(
        content=json.dumps({
            "status": "healthy",
            "database": db_status,
            "timestamp": datetime.datetime.now().isoformat()
        }),
        media_type="application/json",
        status_code=200
    )

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
@app.get("/api/v1/health", include_in_schema=False)
def health_check(db: Session = Depends(get_db)):
    # 检查数据库连接
    try:
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"

    return Response(
        content=json.dumps({
            "status": "healthy",
            "database": db_status,
            "timestamp": datetime.datetime.now().isoformat()
        }),
        media_type="application/json",
        status_code=200
    )