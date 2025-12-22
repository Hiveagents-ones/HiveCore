from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
import uuid
from contextlib import asynccontextmanager

from .routers import register
from .core.security import setup_security
from .models import Base, engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up application...")
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown
    logger.info("Shutting down application...")

app = FastAPI(
    title="Gym Membership System",
    description="A gym membership management system API",
    version="1.0.0",
    lifespan=lifespan
)

# Setup security
setup_security(app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(
        f"Request started - ID: {request_id} - Method: {request.method} - Path: {request.url.path}"
    )
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        logger.info(
            f"Request completed - ID: {request_id} - Status: {response.status_code} - "
            f"Duration: {process_time:.4f}s"
        )
        
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Request failed - ID: {request_id} - Error: {str(e)} - Duration: {process_time:.4f}s"
        )
        raise

# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(
        f"HTTP exception - Status: {exc.status_code} - Detail: {exc.detail} - "
        f"Path: {request.url.path}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled exception - Type: {type(exc).__name__} - Detail: {str(exc)} - "
        f"Path: {request.url.path}",
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error",
            "status_code": 500,
            "path": request.url.path
        }
    )

# Include routers
app.include_router(register.router, prefix="/api/v1", tags=["register"])

@app.get("/")
async def root():
    return {"message": "Gym Membership System API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}