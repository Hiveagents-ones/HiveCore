from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from .routers import members, courses, schedules, payments, bookings
from .database import engine, Base, get_db

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Gym Management API",
    description="API for managing gym members, courses, schedules and payments",
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
    schedules.router,
    prefix="/api/v1/schedules",
    tags=["schedules"],
    dependencies=[Depends(get_db)]
)

app.include_router(
    payments.router,
    prefix="/api/v1/payments",
    tags=["payments"],
    dependencies=[Depends(get_db)]
)

app.include_router(
    bookings.router,
    prefix="/api/v1/members/{member_id}/bookings",
    tags=["bookings"],
    dependencies=[Depends(get_db)]
)

@app.get("/")
def root():
    return {"message": "Gym Management API is running"}