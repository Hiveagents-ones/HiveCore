from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .database import Base, get_db


class AuditLog(Base):
    """Audit log model for tracking system activities"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=True)
    user_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(String(500), nullable=True)


class AuditService:
    """Service for recording audit logs"""

    @staticmethod
    def log_action(
        db: Session,
        action: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        user_id: Optional[int] = None,
        details: Optional[str] = None
    ):
        """
        Record an audit log entry
        
        Args:
            db: Database session
            action: Action performed (e.g., 'create', 'update', 'delete')
            entity_type: Type of entity affected (e.g., 'member', 'course')
            entity_id: ID of the affected entity
            user_id: ID of the user performing the action
            details: Additional details about the action
        """
        log_entry = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            details=details
        )
        db.add(log_entry)
        db.commit()

    @staticmethod
    def get_logs(db: Session, skip: int = 0, limit: int = 100):
        """
        Retrieve audit logs with pagination
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of audit log entries
        """
        return db.query(AuditLog).offset(skip).limit(limit).all()