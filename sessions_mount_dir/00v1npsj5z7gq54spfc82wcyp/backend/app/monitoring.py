from fastapi import Request, Response
from fastapi.routing import APIRoute
from typing import Callable
import time
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from datetime import datetime


# Prometheus metrics definitions
REQUEST_COUNT = Counter(
    'api_request_count',
    'API Request Count',
    ['method', 'endpoint', 'http_status']
)

MEMBER_OPERATIONS = Counter(
    'member_operations_count',
    'Member Operations Count',
    ['operation_type', 'status']
)

REQUEST_LATENCY = Histogram(
    'api_request_latency_seconds',
    'API Request Latency',
    ['method', 'endpoint']
)

MEMBER_LATENCY = Histogram(
    'member_operations_latency_seconds',
    'Member Operations Latency',
    ['operation_type']
)

MEMBER_AGE_GAUGE = Gauge(
    'member_age_gauge',
    'Member Age Distribution',
    ['age_group']
)
    'member_operations_latency_seconds',
    'Member Operations Latency',
    ['operation_type']
)

ACTIVE_REQUESTS = Gauge(
    'api_active_requests',
    'Active API Requests'
)

ACTIVE_MEMBERS = Gauge(
    'active_members_count',
    'Current Active Members Count'
)

MEMBER_TYPE_COUNTER = Counter(

MEMBER_ACTIVITY_COUNTER = Counter(
    'member_activity_count',
    'Member Activity Count',
    ['member_id', 'activity_type']
)

MEMBER_LAST_ACTIVITY = Gauge(
    'member_last_activity_timestamp',
    'Timestamp of last member activity',
    ['member_id']
)
    'member_type_counter',
    'Member Type Distribution',
    ['membership_type']
)
    'active_members_count',
    'Current Active Members Count'
)

class PrometheusMiddleware:
    async def track_member_activity(self, member_id: str, activity_type: str):
        """Track member activity metrics"""
        MEMBER_ACTIVITY_COUNTER.labels(member_id, activity_type).inc()
        MEMBER_LAST_ACTIVITY.labels(member_id).set_to_current_time()
    async def track_member_operation(self, operation_type: str, status: str, duration: float, member_data: dict = None):
        """Track member operations with metrics"""
        MEMBER_OPERATIONS.labels(operation_type, status).inc()
        MEMBER_LATENCY.labels(operation_type).observe(duration)
        if operation_type == 'create':
            # Track member activity
            if member_data:
                await self.track_member_activity(
                    member_data.get('id', 'unknown'),
                    'account_created'
                )
            ACTIVE_MEMBERS.inc()
            if member_data:
                # Track member type distribution
                MEMBER_TYPE_COUNTER.labels(member_data.get('membership_type', 'unknown')).inc()
                # Track age group distribution
                age = member_data.get('age', 0)
                age_group = f"{(age // 10) * 10}-{(age // 10) * 10 + 9}" if age >= 0 else "unknown"
                MEMBER_AGE_GAUGE.labels(age_group).inc()
        elif operation_type == 'delete':
            # Track member activity
            if member_data:
                await self.track_member_activity(
                    member_data.get('id', 'unknown'),
                    'account_deleted'
                )
            ACTIVE_MEMBERS.dec()
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)

        start_time = time.time()
        request = Request(scope, receive)
        method = request.method
        endpoint = request.url.path

        ACTIVE_REQUESTS.inc()

        async def send_wrapper(response):
            if response['type'] == 'http.response.start':
                status_code = response['status']
                REQUEST_COUNT.labels(method, endpoint, status_code).inc()
                REQUEST_LATENCY.labels(method, endpoint).observe(time.time() - start_time)
                ACTIVE_REQUESTS.dec()
            await send(response)

        await self.app(scope, receive, send_wrapper)

class MetricsRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            start_time = time.time()
            response = await original_route_handler(request)
            process_time = time.time() - start_time
            
            REQUEST_LATENCY.labels(
                request.method,
                request.url.path
            ).observe(process_time)
            
            return response

        return custom_route_handler

def setup_metrics(app):
    from fastapi import Depends
    from .database import get_db
    from sqlalchemy.orm import Session
    from .schemas.member import MemberCreate, MemberUpdate
    
    @app.middleware("http")
    async def member_operations_middleware(request: Request, call_next):
        if not request.url.path.startswith('/api/v1/members'):
            return await call_next(request)
            
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        method = request.method
        status_code = response.status_code
        
        if method == 'POST' and status_code == 201:
            operation_type = 'create'
        elif method == 'PUT' and status_code == 200:
            operation_type = 'update'
        elif method == 'DELETE' and status_code == 204:
            operation_type = 'delete'
        else:
            operation_type = 'other'
            
        status = 'success' if status_code < 400 else 'failed'
        
        # Get the Prometheus middleware instance
        prom_middleware = next(m for m in request.app.user_middleware 
                             if m.cls == PrometheusMiddleware)
        # Get member data from request body for create operations
        member_data = None
        if operation_type == 'create' and request.method == 'POST':
            try:
                member_data = await request.json()
            except:
                pass
        
        await prom_middleware.cls.track_member_operation(
            operation_type, 
            status, 
            process_time,
            member_data
        )
        
        return response
    """Setup Prometheus metrics for the application"""
    app.add_middleware(PrometheusMiddleware)
    app.router.route_class = MetricsRoute
    
    @app.get('/metrics')
    async def metrics():
        return Response(
            content=generate_latest(REGISTRY),
            media_type='text/plain'
        )