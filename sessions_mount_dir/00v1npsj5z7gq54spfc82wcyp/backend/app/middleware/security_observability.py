from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from ..services.payment_security import validate_payment_request
from ..services.payment_integrity import check_payment_integrity

logger = logging.getLogger(__name__)

class SecurityObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware for security observability that:
    - Logs security-relevant request information
    - Validates payment-related requests
    - Tracks suspicious activities
    - Integrates with monitoring systems
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.security_events = []

    async def dispatch(self, request: Request, call_next):
        # Log basic request information
        request_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else None,
            "headers": dict(request.headers)
        }

        try:
            # Special handling for payment endpoints
            if request.url.path.startswith('/api/v1/payments'):
                # Validate payment requests
                try:
                    body = await request.json()
                    validate_payment_request(body)
                    check_payment_integrity(body)
                except ValueError as e:
                    self._log_security_event("INVALID_PAYMENT_REQUEST", str(e), request_info)
                    return JSONResponse(
                        status_code=400,
                        content={"detail": str(e)}
                    )
                except Exception as e:
                    self._log_security_event("PAYMENT_VALIDATION_ERROR", str(e), request_info)
                    return JSONResponse(
                        status_code=500,
                        content={"detail": "Internal server error during payment validation"}
                    )

            # Process request
            response = await call_next(request)

            # Log response status
            request_info["status_code"] = response.status_code
            logger.info("Request processed", extra={"request_info": request_info})

            return response

        except HTTPException as http_exc:
            self._log_security_event("HTTP_ERROR", str(http_exc.detail), request_info)
            raise http_exc
        except Exception as exc:
            self._log_security_event("UNHANDLED_ERROR", str(exc), request_info)
            raise HTTPException(
                status_code=500,
                detail="Internal server error"
            ) from exc

    def _log_security_event(self, event_type: str, message: str, context: Optional[Dict[str, Any]] = None):
        """Log a security event with context"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "message": message,
            "context": context or {}
        }
        self.security_events.append(event)
        logger.warning(f"Security event: {event_type} - {message}", extra={"event": event})

    def get_security_events(self):
        """Get recorded security events for monitoring"""
        return self.security_events
