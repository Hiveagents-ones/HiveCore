import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from ..core.cache import redis_client

logger = logging.getLogger(__name__)

class PerformanceMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.concurrent_requests = 0
        self.max_concurrent = 0

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Increment concurrent requests counter
        self.concurrent_requests += 1
        self.max_concurrent = max(self.max_concurrent, self.concurrent_requests)
        
        # Record start time
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            process_time = time.time() - start_time
            
            # Log performance metrics
            logger.info(
                f"Method: {request.method}, Path: {request.url.path}, "
                f"Status: {response.status_code}, Duration: {process_time:.4f}s, "
                f"Concurrent: {self.concurrent_requests}"
            )
            
            # Store metrics in Redis for monitoring
            try:
                await redis_client.hincrby("performance:requests", "total", 1)
                await redis_client.hincrby("performance:requests", f"status_{response.status_code}", 1)
                await redis_client.hset("performance:current", "concurrent", self.concurrent_requests)
                await redis_client.hset("performance:current", "max_concurrent", self.max_concurrent)
                await redis_client.lpush("performance:response_times", f"{process_time:.4f}")
                await redis_client.ltrim("performance:response_times", 0, 999)  # Keep last 1000 entries
            except Exception as e:
                logger.warning(f"Failed to store performance metrics in Redis: {e}")
            
            # Add performance headers
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Concurrent-Requests"] = str(self.concurrent_requests)
            
            return response
            
        finally:
            # Decrement concurrent requests counter
            self.concurrent_requests -= 1
