from fastapi import Request
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
import time
from typing import Callable
import prometheus_client
from prometheus_client import Counter, Histogram
import jaeger_client
from jaeger_client import Config
from fastapi import status

# Prometheus metrics setup
REQUEST_COUNT = Counter(
    'request_count', 'App Request Count',
    ['method', 'endpoint', 'http_status', 'service']
)
REQUEST_LATENCY = Histogram(
    'request_latency_seconds', 'Request latency',
    ['method', 'endpoint', 'service']
)
PAYMENT_AMOUNT = Histogram(
    'payment_amount', 'Payment transaction amounts',
    ['method', 'endpoint', 'service']
)
PAYMENT_COUNT = Counter(
    'payment_count', 'Payment transaction count',
    ['method', 'endpoint', 'payment_type', 'service']
)
REPORT_GENERATION_TIME = Histogram(
    'report_generation_time_seconds', 'Report generation time',
    ['report_type', 'service']
)

# Jaeger tracer setup
def init_tracer(service_name: str):
    config = Config(
        config={
            'sampler': {
                'type': 'const',
                'param': 1,
            },
            'logging': True,
        },
        service_name=service_name,
    )
    return config.initialize_tracer()

tracer = init_tracer('gym-management-service')

async def observability_middleware(request: Request, call_next: Callable):
    """
    Middleware for collecting metrics and tracing
    """
    start_time = time.time()
    method = request.method
    path = request.url.path
    
    # Start Jaeger span
    with tracer.start_span('http_request') as span:
        span.set_tag('http.method', method)
        span.set_tag('http.path', path)
        # Special handling for payment endpoints
        if '/payments' in path:
        elif '/reports' in path:
            span.set_tag('report.endpoint', True)
            if request.method == 'GET':
                report_type = request.query_params.get('type', 'general')
                span.set_tag('report.type', report_type)
            span.set_tag('payment.endpoint', True)
            if request.method == 'POST':
                try:
                    body = await request.json()
                    if 'amount' in body:
                        span.set_tag('payment.amount', body['amount'])
                        span.set_tag('payment.type', body.get('payment_type', 'unknown'))
                        PAYMENT_COUNT.labels(method, path, body.get('payment_type', 'unknown'), 'payment-service').inc()
                        PAYMENT_AMOUNT.labels(method, path, 'payment-service').observe(float(body['amount']))
                except:
                    pass
        
        try:
            response = await call_next(request)
            
            # Record metrics
            latency = time.time() - start_time
            service_name = (
    'payment-service' if '/payments' in path
    else 'members-service' if '/members' in path
    else 'courses-service' if '/courses' in path
    else 'coaches-service' if '/coaches' in path
    else 'reports-service' if '/reports' in path
    else 'other'
)
REQUEST_COUNT.labels(method, path, response.status_code, service_name).inc()
if '/reports' in path and request.method == 'GET':
    report_type = request.query_params.get('type', 'general')
    REPORT_GENERATION_TIME.labels(report_type, service_name).observe(latency)
            REQUEST_LATENCY.labels(method, path, 'payment-service' if '/payments' in path else 'other').observe(latency)
            
            # Add tracing headers
            span.set_tag('http.status_code', response.status_code)
            span.set_tag('response_time', latency)
            
            return response
            
        except Exception as e:
            span.set_tag('error', True)
            span.log_kv({'exception': str(e)})
            REQUEST_COUNT.labels(method, path, status.HTTP_500_INTERNAL_SERVER_ERROR, 'payment-service' if '/payments' in path else 'reports-service' if '/reports' in path else 'other').inc()
            raise

# FastAPI middleware setup
def get_observability_middleware():
    """
    Returns the observability middleware stack
    """
    return [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        ),
        Middleware(observability_middleware),
    ]