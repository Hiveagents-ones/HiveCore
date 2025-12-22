import logging
import sys
from typing import Optional
from datetime import datetime
from pythonjsonlogger import jsonlogger
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests and responses"""

    async def dispatch(self, request: Request, call_next):
        start_time = datetime.now()
        
        # Log request
        logger.info(
            "HTTP Request",
            extra={
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "timestamp": start_time.isoformat(),
                "event_type": "http_request"
            }
        )

        response = await call_next(request)

        # Log response
        process_time = (datetime.now() - start_time).total_seconds()
        logger.info(
            "HTTP Response",
            extra={
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "process_time": process_time,
                "timestamp": datetime.now().isoformat(),
                "event_type": "http_response"
            }
        )

        return response


def setup_logging(
    level: str = "INFO",
    log_format: str = "json",
    service_name: str = "membership-service"
) -> None:
    """Setup application logging configuration"""

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))

    # Set formatter based on format type
    if log_format.lower() == "json":
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S"
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)

    # Add service name to all logs
    logging.LoggerAdapter(
        root_logger,
        {"service": service_name}
    )


def log_business_event(
    event_type: str,
    user_id: Optional[str] = None,
    membership_id: Optional[str] = None,
    payment_id: Optional[str] = None,
    plan_type: Optional[str] = None,
    amount: Optional[float] = None,
    status: Optional[str] = None,
    details: Optional[dict] = None,
    error: Optional[str] = None
) -> None:
    """Log business events with structured data"""
    
    extra = {
        "event_type": event_type,
        "timestamp": datetime.now().isoformat(),
        "service": "membership-service"
    }

    # Add optional fields if provided
    if user_id:
        extra["user_id"] = user_id
    if membership_id:
        extra["membership_id"] = membership_id
    if payment_id:
        extra["payment_id"] = payment_id
    if plan_type:
        extra["plan_type"] = plan_type
    if amount is not None:
        extra["amount"] = amount
    if status:
        extra["status"] = status
    if details:
        extra.update(details)
    if error:
        extra["error"] = error

    # Determine log level based on event type and status
    if event_type == "payment_success":
        logger.info("Payment Success", extra=extra)
    elif event_type == "payment_failed":
        logger.error("Payment Failed", extra=extra)
    elif event_type == "membership_renewed":
        logger.info("Membership Renewed", extra=extra)
    elif event_type == "membership_expired":
        logger.warning("Membership Expired", extra=extra)
    elif event_type == "payment_initiated":
        logger.info("Payment Initiated", extra=extra)
    elif event_type == "payment_cancelled":
        logger.warning("Payment Cancelled", extra=extra)
    else:
        logger.info(f"Business Event: {event_type}", extra=extra)


# Create module logger
logger = logging.getLogger(__name__)


# Convenience functions for specific business events
def log_payment_success(
    user_id: str,
    payment_id: str,
    membership_id: str,
    plan_type: str,
    amount: float,
    payment_method: str
) -> None:
    """Log successful payment event"""
    log_business_event(
        event_type="payment_success",
        user_id=user_id,
        payment_id=payment_id,
        membership_id=membership_id,
        plan_type=plan_type,
        amount=amount,
        details={"payment_method": payment_method}
    )


def log_payment_failed(
    user_id: str,
    payment_id: str,
    membership_id: str,
    plan_type: str,
    amount: float,
    error_message: str,
    error_code: Optional[str] = None
) -> None:
    """Log failed payment event"""
    log_business_event(
        event_type="payment_failed",
        user_id=user_id,
        payment_id=payment_id,
        membership_id=membership_id,
        plan_type=plan_type,
        amount=amount,
        error=error_message,
        details={"error_code": error_code} if error_code else None
    )


def log_membership_renewed(
    user_id: str,
    membership_id: str,
    plan_type: str,
    old_expiry: str,
    new_expiry: str,
    payment_id: str
) -> None:
    """Log membership renewal event"""
    log_business_event(
        event_type="membership_renewed",
        user_id=user_id,
        membership_id=membership_id,
        plan_type=plan_type,
        payment_id=payment_id,
        details={
            "old_expiry": old_expiry,
            "new_expiry": new_expiry,
            "duration_days": (
                datetime.fromisoformat(new_expiry) - 
                datetime.fromisoformat(old_expiry)
            ).days
        }
    )


def log_payment_initiated(
    user_id: str,
    membership_id: str,
    plan_type: str,
    amount: float,
    payment_method: str
) -> None:
    """Log payment initiation event"""
    log_business_event(
        event_type="payment_initiated",
        user_id=user_id,
        membership_id=membership_id,
        plan_type=plan_type,
        amount=amount,
        details={"payment_method": payment_method}
    )
