from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from .routers import members, courses, coaches, payments, reports
from .database import engine, Base, get_db

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="会员管理系统",
    description="健身房会员管理API",
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
    reports.router,
    prefix="/api/v1",
    tags=["reports"],
    dependencies=[Depends(get_db)]
)

@app.get("/")
async def root():
    return {"message": "Welcome to Gym Management System API"}