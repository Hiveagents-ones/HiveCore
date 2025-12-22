from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from .middleware.logging import setup_logging_middleware
import time

from .routers import members, courses, bookings, coaches, payments, reports, schedules, coach_leaves
from .database import engine, Base, get_db

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="会员信息管理系统",
    description="会员信息管理API接口",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json"
)

# Setup logging middleware
app = setup_logging_middleware(app)
# Authentication middleware
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    members.router,
    prefix="/api/v1/members",
    tags=["members"],
    dependencies=[Depends(get_db)]
)

app.include_router(
    courses.router,
    prefix="/api/v1/courses",
    tags=["courses"],
    dependencies=[Depends(get_db)]
)

app.include_router(
    bookings.router,
    prefix="/api/v1/bookings",
    tags=["bookings"],
    dependencies=[Depends(get_db)]
)

app.include_router(
    coaches.router,
    prefix="/api/v1/coaches",
    tags=["coaches"],
    dependencies=[Depends(get_db)]
)

app.include_router(
    payments.router,
    prefix="/api/v1/payments",
    tags=["payments"],
    dependencies=[Depends(get_db)]
)

app.include_router(
    reports.router,
    prefix="/api/v1/reports",
    tags=["reports"],
    dependencies=[Depends(get_db)]
)

app.include_router(
    schedules.router,
    prefix="/api/v1/schedules",
    tags=["schedules"],
    dependencies=[Depends(get_db)]
)

@app.get("/")
async def root():
    return {"message": "会员信息管理系统API"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}