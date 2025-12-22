from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from .routers import members, courses, coaches, payments
from .database import engine, Base, get_db

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Gym Management System",
    description="API for managing gym members, courses, coaches and payments",
    version="1.0.0"
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

@app.get("/")
def root():
    return {"message": "Gym Management System API"}