from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi import status

from .routers import members, courses, coaches, payments, registrations, coach_schedules, payment_methods
from .database import engine, Base, get_db

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="会员管理系统 API",
    description="健身房会员管理系统后端API",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json"
)

# CORS configuration
# Force HTTPS
app.add_middleware(
    HTTPSRedirectMiddleware
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    members.router,
    prefix="/api/v1/members",
    tags=["members"]
)

app.include_router(
    courses.router,
    prefix="/api/v1/courses",
    tags=["courses"]
)

app.include_router(
    coaches.router,
    prefix="/api/v1/coaches",
    tags=["coaches"]
)

app.include_router(
    payments.router,
    prefix="/api/v1/payments",
    tags=["payments"]
)

app.include_router(
    registrations.router,
    prefix="/api/v1/registrations",
    tags=["registrations"]
)

app.include_router(
    coach_schedules.router,
    prefix="/api/v1/coach_schedules",
    tags=["coach_schedules"]
)

app.include_router(
    payment_methods.router,
    prefix="/api/v1/payment_methods",
    tags=["payment_methods"]
)
@app.get("/")
async def root():
    return {"message": "Welcome to Gym Membership Management System API"}

@app.get("/health")
@app.get("/api/v1/members/status", status_code=status.HTTP_200_OK)
async def check_members_service():
    """
    检查会员服务状态
    """
    return {
        "service": "members",
        "status": "active",
        "version": "1.0.0",
        "database": "connected"
    }
async def health_check():
    return {"status": "healthy"}

