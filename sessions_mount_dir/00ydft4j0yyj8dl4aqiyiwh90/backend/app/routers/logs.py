from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from enum import Enum

from ..models.log import OperationLog, SystemLog
from ..database import get_db


class OperationAction(str, Enum):
    """Operation log action types"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BOOK = "book"
    CANCEL = "cancel"
    LOGIN = "login"
    LOGOUT = "logout"
    RESERVE = "reserve"
    UNRESERVE = "unreserve"
    """Operation log action types"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BOOK = "book"
    CANCEL = "cancel"
    LOGIN = "login"
    LOGOUT = "logout"

router = APIRouter(
    prefix="/api/v1/logs",
    tags=["logs"],
    responses={404: {"description": "Not found"}},
)


@router.get("/operations", response_model=List[dict])
def get_operation_logs(
    """
    Retrieve operation logs with optional filters
    
    Filters:
    - member_id: Filter by member ID
    - action: Filter by action type (create/update/delete/book/cancel/login/logout/reserve/unreserve)
    - entity_type: Filter by entity type
    - start_date: Start date filter (inclusive)
    - end_date: End date filter (inclusive)
    - limit: Limit number of results (default: 100)
    """
    db: Session = Depends(get_db),
    member_id: Optional[int] = Query(None, description="Filter by member ID"),
    action: Optional[OperationAction] = Query(None, description="Filter by action type. Possible values: create, update, delete, book, cancel, login, logout, reserve, unreserve"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    start_date: Optional[datetime] = Query(
        None,
        description="Start date filter (inclusive). Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS"
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="End date filter (inclusive). Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS"
    ),
    limit: int = Query(100, description="Limit number of results"),
):
    """
    Retrieve operation logs with optional filters
    """
    query = db.query(OperationLog)

    if member_id is not None:
        query = query.filter(OperationLog.member_id == member_id)
    if action is not None:
        query = query.filter(OperationLog.action == action.value)
    if entity_type is not None:
        query = query.filter(OperationLog.entity_type == entity_type)
    if start_date is not None:
        query = query.filter(OperationLog.created_at >= start_date)
    if end_date is not None:
        query = query.filter(OperationLog.created_at <= end_date)

    logs = query.order_by(OperationLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "member_id": log.member_id,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "created_at": log.created_at,
        }
        for log in logs
    ]


@router.get("/systems", response_model=List[dict])
def get_system_logs(
    """
    Retrieve system logs with optional filters
    
    Filters:
    - level: Filter by log level
    - module: Filter by module name
    - days: Number of days to look back (default: 7)
    - limit: Limit number of results (default: 100)
    """
    db: Session = Depends(get_db),
    level: Optional[str] = Query(None, description="Filter by log level"),
    module: Optional[str] = Query(None, description="Filter by module name"),
    days: int = Query(7, description="Number of days to look back"),
    limit: int = Query(100, description="Limit number of results"),
):
    """
    Retrieve system logs with optional filters
    """
    query = db.query(SystemLog)

    if level is not None:
        query = query.filter(SystemLog.level == level)
    if module is not None:
        query = query.filter(SystemLog.module == module)

    cutoff_date = datetime.utcnow() - timedelta(days=days)
    query = query.filter(SystemLog.created_at >= cutoff_date)

    logs = query.order_by(SystemLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "level": log.level,
            "module": log.module,
            "message": log.message,
            "stack_trace": log.stack_trace,
            "created_at": log.created_at,
        }
        for log in logs
    ]