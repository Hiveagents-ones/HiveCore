"""Main FastAPI application.

This module initializes and configures the FastAPI application.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database import close_db, init_db
from app.routers import members


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Startup: Initialize database
    if settings.DEBUG:
        await init_db()
    yield
    # Shutdown: Close database connections
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    description="Member Management API",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)


# Include routers
app.include_router(members.router)


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint.

    Returns:
        dict: Welcome message and API info
    """
    return {
        "message": "Welcome to Member Management API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        dict: Health status
    """
    return {"status": "healthy"}


# Exception handlers
@app.exception_handler(MemberNotFoundError)
async def member_not_found_handler(request, exc) -> JSONResponse:
    """Handle MemberNotFoundError exceptions.

    Args:
        request: Request instance
        exc: Exception instance

    Returns:
        JSONResponse: Error response
    """
    return JSONResponse(
        status_code=404,
        content={"error": "Member not found", "detail": str(exc)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc) -> JSONResponse:
    """Handle validation errors.

    Args:
        request: Request instance
        exc: Exception instance

    Returns:
        JSONResponse: Error response
    """
    return JSONResponse(
        status_code=422,
        content={"error": "Validation error", "detail": exc.errors()},
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request, exc) -> JSONResponse:
    """Handle SQLAlchemy errors.

    Args:
        request: Request instance
        exc: Exception instance

    Returns:
        JSONResponse: Error response
    """
    return JSONResponse(
        status_code=500,
        content={"error": "Database error", "detail": str(exc) if settings.DEBUG else "Internal server error"},
    )


# Import MemberNotFoundError for exception handler
from app.services.member_service import MemberNotFoundError  # noqa: E402
