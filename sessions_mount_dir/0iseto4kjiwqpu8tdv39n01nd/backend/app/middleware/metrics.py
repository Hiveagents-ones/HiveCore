from fastapi import Request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
import time
from typing import Callable

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

PAYMENT_SUCCESS_RATE = Counter(
    'payment_success_total',
    'Total successful payments',
    ['payment_method']
)

PAYMENT_FAILURE_RATE = Counter(
    'payment_failure_total',
    'Total failed payments',
    ['payment_method', 'error_type']
)

PAYMENT_DURATION = Histogram(
    'payment_processing_duration_seconds',
    'Payment processing duration in seconds',
    ['payment_method']
)

SUBSCRIPTION_RENEWAL = Counter(
    'subscription_renewal_total',
    'Total subscription renewals',
    ['status']
)

class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Record metrics
        method = request.method
        endpoint = request.url.path
        status_code = str(response.status_code)
        
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc()
        
        REQUEST_DURATION.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        return response

def record_payment_success(payment_method: str, duration: float):
    """Record successful payment metrics"""
    PAYMENT_SUCCESS_RATE.labels(payment_method=payment_method).inc()
    PAYMENT_DURATION.labels(payment_method=payment_method).observe(duration)

def record_payment_failure(payment_method: str, error_type: str, duration: float):
    """Record failed payment metrics"""
    PAYMENT_FAILURE_RATE.labels(
        payment_method=payment_method,
        error_type=error_type
    ).inc()
    PAYMENT_DURATION.labels(payment_method=payment_method).observe(duration)

def record_subscription_renewal(status: str):
    """Record subscription renewal metrics"""
    SUBSCRIPTION_RENEWAL.labels(status=status).inc()

def metrics_endpoint():
    """Return Prometheus metrics"""
    return StreamingResponse(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )