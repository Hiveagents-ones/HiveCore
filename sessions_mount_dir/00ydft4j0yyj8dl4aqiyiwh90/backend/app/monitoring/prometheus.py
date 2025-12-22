from fastapi import Request
from fastapi.routing import APIRoute
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from starlette.responses import Response
import time

# Metrics definitions
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP Requests',
    ['method', 'path', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP Request latency',
    ['method', 'path']
)

ACTIVE_REQUESTS = Gauge(
    'http_active_requests',
    'Active HTTP Requests'
)

MEMBER_OPERATIONS = Counter(
    'member_operations_total',
    'Total Member Operations',
    ['operation_type', 'status', 'endpoint']
)

MEMBER_REGISTRATION_LATENCY = Histogram(
    'member_registration_duration_seconds',
    'Member Registration Latency'
)

ACTIVE_MEMBERS = Gauge(
    'active_members_count',
    'Current Active Members Count'
)
    'http_active_requests',
    'Active HTTP Requests'
)

class PrometheusMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)

        start_time = time.time()
        path = scope['path']
        method = scope['method']

        ACTIVE_REQUESTS.inc()

        async def wrapped_send(response):
            if response['type'] == 'http.response.start':
                status_code = response['status']
                REQUEST_COUNT.labels(method=method, path=path, status_code=status_code).inc()
                REQUEST_LATENCY.labels(method=method, path=path).observe(time.time() - start_time)
                ACTIVE_REQUESTS.dec()
            await send(response)

        await self.app(scope, receive, wrapped_send)

def metrics(request: Request):
    return Response(
        content=generate_latest(REGISTRY),
        media_type='text/plain'
    )

def setup_prometheus(app):
    # Add middleware
    app.add_middleware(PrometheusMiddleware)

    # Add metrics endpoint
    app.add_route('/metrics', metrics, methods=['GET'])

    # Track member operations
    @app.middleware('http')
    async def track_member_operations(request: Request, call_next):
        if request.url.path.startswith('/api/v1/members'):
            start_time = time.time()
            operation_type = request.method.lower()
            
            try:
                response = await call_next(request)
                MEMBER_OPERATIONS.labels(
                    operation_type=operation_type,
                    status=response.status_code,
                    endpoint=request.url.path
                ).inc()
                
                if operation_type == 'post':
                    MEMBER_REGISTRATION_LATENCY.observe(time.time() - start_time)
                
                return response
            except Exception as e:
                MEMBER_OPERATIONS.labels(
                    operation_type=operation_type,
                    status='500',
                    endpoint=request.url.path
                ).inc()
                raise e

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:
                elif operation_type == 'get':
                    ACTIVE_MEMBERS.inc()
                elif operation_type == 'delete':
                    ACTIVE_MEMBERS.dec()