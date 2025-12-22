from prometheus_client import Counter, Histogram, Gauge
from fastapi import Request

# Member related metrics
# Schedule related metrics
SCHEDULE_CREATE_COUNT = Counter(
    'schedule_create_total',
    'Total number of schedule creations'
)

SCHEDULE_UPDATE_COUNT = Counter(
    'schedule_update_total',
    'Total number of schedule updates'
)

SCHEDULE_DELETE_COUNT = Counter(
    'schedule_delete_total',
    'Total number of schedule deletions'
)

SCHEDULE_READ_COUNT = Counter(
    'schedule_read_total',
    'Total number of schedule reads'
)

SCHEDULE_CONFLICT_COUNT = Counter(
    'schedule_conflict_total',
    'Total number of schedule conflicts detected'
)
MEMBER_CREATE_COUNT = Counter(
    'member_create_total',
    'Total number of member creations'
)

MEMBER_UPDATE_COUNT = Counter(
    'member_update_total',
    'Total number of member updates'
)

MEMBER_DELETE_COUNT = Counter(
    'member_delete_total',
    'Total number of member deletions'
)

MEMBER_READ_COUNT = Counter(
    'member_read_total',
    'Total number of member reads'
)

# API performance metrics
API_REQUEST_COUNT = Counter(
    'api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'http_status']
)

API_REQUEST_LATENCY = Histogram(
    'api_request_latency_seconds',
    'API request latency in seconds',
    ['method', 'endpoint']
)

# Database metrics
DB_CONNECTION_GAUGE = Gauge(
    'db_connections_total',
    'Current number of database connections'
)

DB_QUERY_LATENCY = Histogram(
    'db_query_latency_seconds',
    'Database query latency in seconds'
)

def record_api_metrics(request: Request, response, duration: float):
    """
    Record API request metrics
    Args:
        request: FastAPI Request object
        response: FastAPI Response object
        duration: Request duration in seconds
    """
    method = request.method
    endpoint = request.url.path
    status_code = response.status_code
    
    # Skip metrics for the /metrics endpoint itself
    if endpoint == '/metrics':
        return
    
    API_REQUEST_COUNT.labels(method=method, endpoint=endpoint, http_status=status_code).inc()
    API_REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)