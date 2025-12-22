import json
from functools import wraps
from typing import Any, Callable, Dict, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.audit_log import AuditLog

from datetime import datetime


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically log HTTP requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get user info from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        
        # Get client info
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # Process the request
        response = await call_next(request)
        
        # Only log if user is authenticated and response is successful
        if user_id and response.status_code < 400:
            # Get database session
            db: Session = next(get_db())
            try:
                # Create audit log entry
                audit_log = AuditLog(
                    user_id=user_id,
                    action="HTTP_REQUEST",
                    resource_type="API",
                    resource_id=f"{request.method} {request.url.path}",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    description=f"{request.method} request to {request.url.path}"
                )
                db.add(audit_log)
                db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()
        
        return response


def audit_action(
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    get_old_values: Optional[Callable[[Any], Dict]] = None,
    get_new_values: Optional[Callable[[Any], Dict]] = None,
    description: Optional[str] = None
):
    """Decorator to audit function actions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get database session from kwargs or create new one
            db = kwargs.get("db")
            if not db:
                db = next(get_db())
                should_close_db = True
            else:
                should_close_db = False
            
            # Get user info from kwargs (typically from request state)
            user_id = kwargs.get("current_user_id")
            if not user_id and "request" in kwargs:
                user_id = getattr(kwargs["request"].state, "user_id", None)
            
            # Get old values if function is provided
            old_values = None
            if get_old_values:
                try:
                    old_values = get_old_values(*args, **kwargs)
                except Exception:
                    old_values = None
            
            # Execute the function
            result = await func(*args, **kwargs)
            
            # Get new values if function is provided
            new_values = None
            if get_new_values:
                try:
                    new_values = get_new_values(result)
                except Exception:
                    new_values = None
            
            # Get IP and user agent from request if available
            ip_address = None
            user_agent = None
            if "request" in kwargs:
                ip_address = kwargs["request"].client.host if kwargs["request"].client else None
                user_agent = kwargs["request"].headers.get("user-agent")
            
            # Create audit log entry
            if user_id:
                try:
                    audit_log = AuditLog(
                        user_id=user_id,
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        old_values=json.dumps(old_values) if old_values else None,
                        new_values=json.dumps(new_values) if new_values else None,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        description=description or f"{action} on {resource_type}"
                    )
                    db.add(audit_log)
                    db.commit()
                except Exception:
                    db.rollback()
                finally:
                    if should_close_db:
                        db.close()
            
            return result
        return wrapper
    return decorator


def log_member_action(action: str, member_id: Optional[str] = None):
    """Specialized decorator for member-related actions."""
    return audit_action(
        action=action,
        resource_type="MEMBER",
        resource_id=member_id,
        description=f"Member {action.lower()} operation"
    )


def log_user_action(action: str, user_id: Optional[str] = None):
    """Specialized decorator for user-related actions."""
    return audit_action(
        action=action,
        resource_type="USER",
        resource_id=user_id,
        description=f"User {action.lower()} operation"
    )


def log_permission_action(action: str, permission_id: Optional[str] = None):
    """Specialized decorator for permission-related actions."""
    return audit_action(
        action=action,
        resource_type="PERMISSION",
        resource_id=permission_id,
        description=f"Permission {action.lower()} operation"
    )


def log_course_action(action: str, course_id: Optional[str] = None):
    """Specialized decorator for course-related actions."""
    return audit_action(
        action=action,
        resource_type="COURSE",
        resource_id=course_id,
        description=f"Course {action.lower()} operation"
    )


def log_booking_action(action: str, booking_id: Optional[str] = None):
    """Specialized decorator for booking-related actions."""
    return audit_action(
        action=action,
        resource_type="BOOKING",
        resource_id=booking_id,
        description=f"Booking {action.lower()} operation"
    )


def create_audit_log(
    db: Session,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    old_values: Optional[Dict] = None,
    new_values: Optional[Dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    description: Optional[str] = None
) -> AuditLog:
    """Create and save an audit log entry."""
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        old_values=json.dumps(old_values) if old_values else None,
        new_values=json.dumps(new_values) if new_values else None,
        ip_address=ip_address,
        user_agent=user_agent,
        description=description or f"{action} on {resource_type}",
        created_at=datetime.utcnow()
    )
    db.add(audit_log)
    db.commit()
    return audit_log