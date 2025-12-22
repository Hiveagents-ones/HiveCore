from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List

from ..database import get_db
from ..schemas.audit import AuditLog, AuditLogCreate
from ..models import AuditLog as AuditLogModel

router = APIRouter(
    prefix="/api/v1/audit",
    tags=["audit"],
    responses={404: {"description": "Not found"}},
)

@router.get("/logs", response_model=List[AuditLog])
def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    action: str = None,
    entity_type: str = None,
    start_date: datetime = None,
    end_date: datetime = None,
    db: Session = Depends(get_db)
):
    """
    Retrieve audit logs with optional filtering.
    
    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        action: Filter by action type (e.g., 'create', 'update', 'delete')
        entity_type: Filter by entity type (e.g., 'member', 'course')
        start_date: Filter logs after this date
        end_date: Filter logs before this date
        
    Returns:
        List of audit log records
    """
    query = db.query(AuditLogModel)
    
    if action:
        query = query.filter(AuditLogModel.action == action)
    if entity_type:
        query = query.filter(AuditLogModel.entity_type == entity_type)
    if start_date:
        query = query.filter(AuditLogModel.timestamp >= start_date)
    if end_date:
        query = query.filter(AuditLogModel.timestamp <= end_date)
    
    return query.order_by(AuditLogModel.timestamp.desc()).offset(skip).limit(limit).all()

@router.post("/logs", response_model=AuditLog)
def create_audit_log(
    audit_log: AuditLogCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new audit log record.
    
    Args:
        audit_log: Audit log data to create
        
    Returns:
        The created audit log record
    """
    db_audit_log = AuditLogModel(**audit_log.dict())
    db.add(db_audit_log)
    db.commit()
    db.refresh(db_audit_log)
    return db_audit_log

@router.get("/logs/{log_id}", response_model=AuditLog)
def get_audit_log(
    log_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve a specific audit log by ID.
    
    Args:
        log_id: ID of the audit log to retrieve
        
    Returns:
        The requested audit log record
    """
    audit_log = db.query(AuditLogModel).filter(AuditLogModel.id == log_id).first()
    if not audit_log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return audit_log