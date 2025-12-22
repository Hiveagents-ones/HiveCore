from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from .routers import (
    members,
    cards,
    courses,
    coaches,
    payments,
    bookings,
    schedules,
    coach_schedules
)
from .database import engine, Base, get_db

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Gym Management System API",
    description="API for managing gym members, courses, coaches and payments",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    contact={
        "name": "API Support",
        "url": "https://aodAQY4i.hivecore.local/_",
        "email": "support@gymmanagement.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(members.router, prefix="/api/v1/members", tags=["members"])
app.include_router(cards.router, prefix="/api/v1/members/{member_id}/cards", tags=["member cards"])
app.include_router(courses.router, prefix="/api/v1/courses", tags=["courses"])
app.include_router(coaches.router, prefix="/api/v1/coaches", tags=["coaches"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(bookings.router, prefix="/api/v1/bookings", tags=["bookings"])
app.include_router(schedules.router, prefix="/api/v1/courses/{course_id}/schedules", tags=["course schedules"])
app.include_router(coach_schedules.router, prefix="/api/v1/coaches/schedules", tags=["coach schedules"])

@app.get("/")
async def root():
    return {"message": "Gym Management System API"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}