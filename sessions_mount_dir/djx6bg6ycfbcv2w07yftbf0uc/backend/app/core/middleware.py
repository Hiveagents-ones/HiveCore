import uuid
import time
import logging
from typing import Callable
from fastapi import Request, Response, HTTPException
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse
from starlette.types import ASGIApp
import redis
from ..config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Redis client for rate limiting
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to generate and attach a unique request ID to each request."""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log request and response details."""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request started",
            extra={
                "request_id": getattr(request.state, "request_id", "unknown"),
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent")
            }
        )
        
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Request completed",
            extra={
                "request_id": getattr(request.state, "request_id", "unknown"),
                "status_code": response.status_code,
                "process_time": round(process_time, 4)
            }
        )
        
        response.headers["X-Process-Time"] = str(round(process_time, 4))
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to implement rate limiting based on client IP."""
    
    def __init__(self, app: ASGIApp, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls  # Number of allowed calls
        self.period = period  # Time period in seconds
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        
        try:
            # Check current count in Redis
            current_count = redis_client.get(f"rate_limit:{client_ip}")
            
            if current_count is None:
                # First request from this IP
                redis_client.setex(f"rate_limit:{client_ip}", self.period, 1)
            else:
                # Increment count
                new_count = redis_client.incr(f"rate_limit:{client_ip}")
                
                if new_count > self.calls:
                    # Rate limit exceeded
                    logger.warning(
                        f"Rate limit exceeded",
                        extra={
                            "request_id": getattr(request.state, "request_id", "unknown"),
                            "client_ip": client_ip,
                            "current_count": new_count,
                            "limit": self.calls
                        }
                    )
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": "Rate limit exceeded. Please try again later.",
                            "error_code": "RATE_LIMIT_EXCEEDED"
                        }
                    )
        except redis.RedisError as e:
            # If Redis is unavailable, log the error but allow the request
            logger.error(
                f"Redis error in rate limiting: {str(e)}",
                extra={
                    "request_id": getattr(request.state, "request_id", "unknown"),
                    "client_ip": client_ip
                }
            )
        
        return await call_next(request)

class I18nMiddleware(BaseHTTPMiddleware):
    """Middleware to handle internationalization based on Accept-Language header."""
    
    def __init__(self, app: ASGIApp, default_language: str = "en"):
        super().__init__(app)
        self.default_language = default_language
        self.supported_languages = ["en", "zh", "es", "fr", "de", "ja"]
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Get language from Accept-Language header
        accept_language = request.headers.get("accept-language", "")
        
        # Parse Accept-Language header
        languages = [lang.split(";")[0].strip() for lang in accept_language.split(",")]
        
        # Find first supported language
        selected_language = self.default_language
        for lang in languages:
            if lang in self.supported_languages:
                selected_language = lang
                break
            # Check for language prefix (e.g., "en-US" -> "en")
            lang_prefix = lang.split("-")[0]
            if lang_prefix in self.supported_languages:
                selected_language = lang_prefix
                break
        
        # Store selected language in request state
        request.state.language = selected_language
        
        response = await call_next(request)
        
        # Add language to response headers
        response.headers["Content-Language"] = selected_language
        
        return response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to responses."""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response

class CORSMiddleware(BaseHTTPMiddleware):
    """Middleware to handle CORS headers."""
    
    def __init__(self, app: ASGIApp, allow_origins: list = None, allow_methods: list = None, allow_headers: list = None):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        origin = request.headers.get("origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
        else:
            response = await call_next(request)
        
        # Add CORS headers
        if "*" in self.allow_origins or (origin and origin in self.allow_origins):
            response.headers["Access-Control-Allow-Origin"] = origin or "*"
        
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "86400"  # 24 hours
        
        return response