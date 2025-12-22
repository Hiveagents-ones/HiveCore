import logging
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable for trace ID
TRACE_ID: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)


class StructuredLogger:
    """Structured logger with trace ID support."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Create console handler with structured formatting
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s - trace_id=%(trace_id)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def _log(self, level: int, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log with trace ID and extra context."""
        trace_id = TRACE_ID.get()
        log_extra = {'trace_id': trace_id or 'no-trace'}
        if extra:
            log_extra.update(extra)
        self.logger.log(level, message, extra=log_extra)
    
    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, kwargs)
    
    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, kwargs)


class TraceMiddleware(BaseHTTPMiddleware):
    """Middleware to inject and propagate trace IDs."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate or extract trace ID
        trace_id = request.headers.get('X-Trace-ID') or str(uuid.uuid4())
        
        # Set trace ID in context
        token = TRACE_ID.set(trace_id)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add trace ID to response headers
            response.headers['X-Trace-ID'] = trace_id
            
            return response
        finally:
            # Reset context
            TRACE_ID.reset(token)


def get_trace_id() -> Optional[str]:
    """Get current trace ID from context."""
    return TRACE_ID.get()


def init_logger(name: str) -> StructuredLogger:
    """Initialize a structured logger."""
    return StructuredLogger(name)


# Default logger instance
logger = init_logger(__name__)
