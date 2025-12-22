from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from .routers import members, courses, coaches, payments
from .database import engine, Base, get_db

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Gym Management API",
    description="API for gym member and course management",
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
app.include_router(members.router, prefix="/api/v1/members", tags=["members"])
app.include_router(courses.router, prefix="/api/v1/courses", tags=["courses"])
app.include_router(coaches.router, prefix="/api/v1/coaches", tags=["coaches"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])

@app.get("/")
async def root():
    return {"message": "Gym Management API"}