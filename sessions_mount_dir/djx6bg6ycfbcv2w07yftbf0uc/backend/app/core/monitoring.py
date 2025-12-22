import time
import psutil
import logging
from typing import Dict, Any, Optional
from functools import wraps
from fastapi import Request, Response
from contextlib import asynccontextmanager
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response as FastAPIResponse

logger = logging.getLogger(__name__)

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

ACTIVE_CONNECTIONS = Gauge(
    'active_connections',
    'Number of active connections'
)

CPU_USAGE = Gauge(
    'cpu_usage_percent',
    'CPU usage percentage'
)

MEMORY_USAGE = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes'
)

class PerformanceMonitor:
    """Performance monitoring and metrics collection"""
    
    def __init__(self):
        self._metrics: Dict[str, Any] = {}
        self._start_time = time.time()
        self._request_counts: Dict[str, int] = {}
        self._response_times: Dict[str, list] = {}
        
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        key = f"{method}:{endpoint}"
        
        # Update request counts
        if key not in self._request_counts:
            self._request_counts[key] = 0
        self._request_counts[key] += 1
        
        # Update response times
        if key not in self._response_times:
            self._response_times[key] = []
        self._response_times[key].append(duration)
        
        # Keep only last 100 response times per endpoint
        if len(self._response_times[key]) > 100:
            self._response_times[key] = self._response_times[key][-100:]
        
        # Update Prometheus metrics
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc()
        
        REQUEST_DURATION.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Update Prometheus gauges
        CPU_USAGE.set(cpu_percent)
        MEMORY_USAGE.set(memory.used)
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used': memory.used,
            'memory_total': memory.total,
            'disk_percent': (disk.used / disk.total) * 100,
            'disk_used': disk.used,
            'disk_total': disk.total,
            'uptime': time.time() - self._start_time
        }
    
    def get_application_metrics(self) -> Dict[str, Any]:
        """Get application-specific metrics"""
        metrics = {
            'total_requests': sum(self._request_counts.values()),
            'endpoint_stats': {}
        }
        
        for endpoint, count in self._request_counts.items():
            response_times = self._response_times.get(endpoint, [])
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            metrics['endpoint_stats'][endpoint] = {
                'request_count': count,
                'avg_response_time': avg_response_time,
                'max_response_time': max(response_times) if response_times else 0,
                'min_response_time': min(response_times) if response_times else 0
            }
        
        return metrics
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics combined"""
        return {
            'system': self.get_system_metrics(),
            'application': self.get_application_metrics(),
            'timestamp': time.time()
        }

# Global monitor instance
monitor = PerformanceMonitor()

def monitor_performance(func):
    """Decorator to monitor function performance"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            logger.debug(f"Function {func.__name__} executed in {duration:.4f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Function {func.__name__} failed after {duration:.4f}s: {str(e)}")
            raise
    return wrapper

async def monitoring_middleware(request: Request, call_next):
    """FastAPI middleware for monitoring requests"""
    start_time = time.time()
    
    # Increment active connections
    ACTIVE_CONNECTIONS.inc()
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Record metrics
        monitor.record_request(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            duration=duration
        )
        
        # Add performance headers
        response.headers["X-Response-Time"] = f"{duration:.4f}"
        
        return response
    
    finally:
        # Decrement active connections
        ACTIVE_CONNECTIONS.dec()

async def metrics_endpoint():
    """Endpoint to expose Prometheus metrics"""
    return FastAPIResponse(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@asynccontextmanager
async def monitor_context(operation_name: str):
    """Context manager for monitoring operations"""
    start_time = time.time()
    logger.info(f"Starting operation: {operation_name}")
    
    try:
        yield
        duration = time.time() - start_time
        logger.info(f"Operation {operation_name} completed in {duration:.4f}s")
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Operation {operation_name} failed after {duration:.4f}s: {str(e)}")
        raise

class DatabaseMonitor:
    """Database performance monitoring"""
    
    def __init__(self):
        self._query_times: Dict[str, list] = {}
        self._query_counts: Dict[str, int] = {}
    
    def record_query(self, query_type: str, duration: float):
        """Record database query metrics"""
        if query_type not in self._query_times:
            self._query_times[query_type] = []
            self._query_counts[query_type] = 0
        
        self._query_times[query_type].append(duration)
        self._query_counts[query_type] += 1
        
        # Keep only last 100 query times per type
        if len(self._query_times[query_type]) > 100:
            self._query_times[query_type] = self._query_times[query_type][-100:]
    
    def get_query_stats(self) -> Dict[str, Any]:
        """Get database query statistics"""
        stats = {}
        
        for query_type, times in self._query_times.items():
            stats[query_type] = {
                'count': self._query_counts[query_type],
                'avg_time': sum(times) / len(times) if times else 0,
                'max_time': max(times) if times else 0,
                'min_time': min(times) if times else 0
            }
        
        return stats

# Global database monitor instance
db_monitor = DatabaseMonitor()

def monitor_database_query(query_type: str):
    """Decorator to monitor database queries"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                db_monitor.record_query(query_type, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                db_monitor.record_query(f"{query_type}_error", duration)
                raise
        return wrapper
    return decorator