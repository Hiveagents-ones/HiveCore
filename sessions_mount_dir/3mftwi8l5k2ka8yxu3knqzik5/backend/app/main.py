from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.routers import members
from app.core.config import settings
from app.core.database import engine
from app.models import member
from app.core.logging import setup_logging
import logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Create database tables
member.Base.metadata.create_all(bind=engine)

# Create FastAPI instance
app = FastAPI(
    title="Membership Management API",
    description="API for managing member information including profiles, contacts, and membership status",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Include routers
app.include_router(members.router, prefix="/api/v1/members", tags=["members"])

@app.on_event("startup")
async def startup_event():
    logger.info("Application startup")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown")

@app.get("/")
async def root():
    return {"message": "Membership Management API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
