from fastapi import Request
from prometheus_client import Counter, Histogram, Gauge
import time

# Prometheus metrics setup
REQUEST_COUNT = Counter(
    'http_requests_total', 'Total HTTP Requests',
    ['method', 'path', 'status', 'service']
)
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds', 'HTTP Request duration',
    ['method', 'path', 'service']
)
ACTIVE_REQUESTS = Gauge(
    'http_requests_in_progress', 'Active HTTP requests'
)

async def metrics_middleware(request: Request, call_next, service_name: str = 'courses'):
    """
    Middleware for collecting Prometheus metrics
    """
    start_time = time.time()
    method = request.method
    endpoint = request.url.path
    
    # Skip metrics for /metrics endpoint itself
    if endpoint == '/metrics':
        return await call_next(request)
    
    ACTIVE_REQUESTS.inc()
    
    try:
        response = await call_next(request)
        http_status = response.status_code
        
        REQUEST_COUNT.labels(method, endpoint, http_status, service_name).inc()
        REQUEST_LATENCY.labels(method, endpoint, service_name).observe(time.time() - start_time)
        
        return response
    except Exception as e:
        REQUEST_COUNT.labels(method, endpoint, 500, service_name).inc()
        raise e
    finally:
        ACTIVE_REQUESTS.dec()