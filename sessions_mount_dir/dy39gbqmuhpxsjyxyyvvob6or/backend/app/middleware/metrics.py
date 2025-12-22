from fastapi import Request, Response
from fastapi.routing import APIRoute
from typing import Callable
import time
from prometheus_client import Counter, Histogram, Gauge
from starlette.middleware.base import BaseHTTPMiddleware

# Prometheus metrics setup
REQUEST_COUNT = Counter(
    ['method', 'path', 'status_code'],
    labelnames=['method', 'path', 'status_code']
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'path', 'status_code']
)

REQUEST_LATENCY = Histogram(
    ['method', 'path'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'path']
)

ACTIVE_REQUESTS = Gauge(
    'http_active_requests',
    'Number of active HTTP requests',
    multiprocess_mode='livesum'
    'http_active_requests',
    'Number of active HTTP requests'
)

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting Prometheus metrics for FastAPI applications.
    """
        # This replaces the __call__ method with the standard BaseHTTPMiddleware interface
        # Track active requests
        ACTIVE_REQUESTS.inc()
        
        # Record start time for latency calculation
        start_time = time.time()
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Get the route path (use raw path if route not found)
            route_path = request.url.path
            if request.scope.get('route'):
                route_path = request.scope['route'].path
            
            # Update metrics
            REQUEST_COUNT.labels(
                method=request.method,
                path=route_path,
                status_code=response.status_code
            ).inc()
            
            REQUEST_LATENCY.labels(
                method=request.method,
                path=route_path
            ).observe(time.time() - start_time)
            
            return response
        finally:
            # Decrement active requests counter
            ACTIVE_REQUESTS.dec()

class PrometheusRoute(APIRoute):
    """
    Custom APIRoute that adds Prometheus metrics for individual routes.
    """
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        
        async def custom_route_handler(request: Request) -> Response:
            # Track active requests
            ACTIVE_REQUESTS.inc()
            
            # Record start time for latency calculation
            start_time = time.time()
            
            try:
                # Process the request
                response = await original_route_handler(request)
                
                # Update metrics
                REQUEST_COUNT.labels(
                    method=request.method,
                    path=self.path,
                    status_code=response.status_code
                ).inc()
                
                REQUEST_LATENCY.labels(
                    method=request.method,
                    path=self.path
                ).observe(time.time() - start_time)
                
                return response
            finally:
                # Decrement active requests counter
                ACTIVE_REQUESTS.dec()
        
        return custom_route_handler

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:
    async def dispatch(self, request: Request, call_next):