from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from .routers import members, courses, coaches, payments, schedules, bookings, fees

# Import database dependencies
from .database import engine, Base, get_db

# Create FastAPI application
app = FastAPI(
    title="Gym Management System",
    description="API for Gym Membership Management",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Include routers with API version prefix
app.include_router(
app.include_router(
    fees.router,
    prefix="/api/v1",
    tags=["fees"],
    dependencies=[Depends(get_db)]
)
    schedules.router,
    prefix="/api/v1",
    tags=["schedules"],
    dependencies=[Depends(get_db)]
)
app.include_router(
    members.router,
    prefix="/api/v1",
    tags=["members"],
    dependencies=[Depends(get_db)]
)
app.include_router(
    courses.router,
    prefix="/api/v1",
    tags=["courses"],
    dependencies=[Depends(get_db)]
)
app.include_router(
    coaches.router,
    prefix="/api/v1",
    tags=["coaches"],
    dependencies=[Depends(get_db)]
)
app.include_router(
    payments.router,
    prefix="/api/v1",
    tags=["payments"],
    dependencies=[Depends(get_db)]
)
app.include_router(
    bookings.router,
    prefix="/api/v1",
    tags=["bookings"],
    dependencies=[Depends(get_db)]
)

@app.get("/")
def root():
    return {"message": "Gym Management System API"}