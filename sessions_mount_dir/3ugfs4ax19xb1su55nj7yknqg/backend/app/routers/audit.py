from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from ..database import get_db, Base
from sqlalchemy import Column, Integer, String, DateTime, Text

router = APIRouter(
    prefix="/api/v1/audit",
    tags=["audit"],
    responses={404: {"description": "Not found"}},
)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    user_id = Column(Integer)
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

@router.get("/logs", response_model=List[dict])
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Retrieve audit logs
    """
    logs = db.query(AuditLog).offset(skip).limit(limit).all()
    return [
        {
            "id": log.id,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "user_id": log.user_id,
            "details": log.details,
            "created_at": log.created_at
        }
        for log in logs
    ]

@router.post("/log")
async def create_audit_log(
    action: str,
    entity_type: str,
    entity_id: int,
    user_id: int = None,
    details: str = None,
    db: Session = Depends(get_db)
):
    """
    Create a new audit log entry
    """
    log = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        details=details
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return {"message": "Audit log created successfully", "log_id": log.id}