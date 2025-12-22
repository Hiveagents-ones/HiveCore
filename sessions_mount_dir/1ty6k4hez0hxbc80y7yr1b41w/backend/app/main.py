from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware

from .routers import members, courses, coaches, payments, coach_schedules
from .database import engine, Base, get_db

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Gym Management System",
    description="API for gym member management and operations",
    version="1.0.0"
)

# Configure CORS
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
    coach_schedules.router,
    prefix="/api/v1/coaches/schedule",
    tags=["coach_schedules"],
    dependencies=[Depends(get_db)]
)

@app.get("/")
async def root():
    return {
        "message": "Welcome to Gym Management System API",
        "version": "1.0.0",
        "documentation": "/docs",
        "available_endpoints": [
            "/api/v1/members",
            "/api/v1/courses",
            "/api/v1/coaches",
            "/api/v1/payments",
            "/api/v1/coaches/schedule"
        ]
    }