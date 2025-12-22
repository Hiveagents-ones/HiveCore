from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from app.routers import members
from app.routers import courses
from app.core.config import settings
from app.core.database import engine
from app.models import member
from app.models import course

# Create database tables
member.Base.metadata.create_all(bind=engine)
course.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Membership Management System API",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configure CORS
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

# Configure Prometheus metrics
Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_group_untemplated=True,
    should_instrument_requests_inprogress=True,
    should_instrument_requests_duration=True,
    excluded_handlers=["/metrics"],
    env_var_name="ENABLE_METRICS",
    inprogress_name="fastapi_inprogress",
    inprogress_labels=True,
).instrument(app).expose(app, include_in_schema=False)

# Include routers
app.include_router(
    members.router,
    prefix=f"{settings.API_V1_STR}/members",
    tags=["members"]
)

app.include_router(
    courses.router,
    prefix=f"{settings.API_V1_STR}/courses",
    tags=["courses"]
)

@app.get("/")
async def root():
    return {
        "message": "Membership Management System API",
        "version": "1.0.0",
        "docs": f"{settings.API_V1_STR}/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}