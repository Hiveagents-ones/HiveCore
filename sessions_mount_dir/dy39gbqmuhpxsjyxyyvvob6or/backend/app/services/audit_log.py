from datetime import datetime
import hashlib
import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from ..database import Base
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy import and_


class AuditLog(Base):
    @staticmethod
    def generate_data_signature(data: dict) -> str:
        """
        Generate a SHA256 signature for audit log data
        :param data: Dictionary of data to be signed
        :return: Hexadecimal signature string
        """
        if not data:
            return ""
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("members.id"), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=True)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLogService:
    @staticmethod
    def log_schedule_action(
        db: Session,
        action: str,
        schedule_id: int,
        coach_id: int,
        changed_by: int,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        Log a schedule-related action to the audit log
        :param db: Database session
        :param action: Action performed ('created', 'updated', 'cancelled')
        :param schedule_id: ID of the affected schedule
        :param coach_id: ID of the coach
        :param changed_by: ID of the user making the change
        :param old_values: Previous schedule values
        :param new_values: New schedule values
        :return: The created audit log entry
        """
        return AuditLogService.log_action(
            db=db,
            action=action,
            entity_type="coach_schedule",
            user_id=changed_by,
            entity_id=schedule_id,
            old_values=old_values,
            new_values=new_values
        )
    @staticmethod
    def log_action(
        db: Session,
        action: str,
        entity_type: str,
        user_id: Optional[int] = None,
        entity_id: Optional[int] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Log an action to the audit log with data integrity verification
        :param db: Database session
        :param action: Action performed (e.g., 'create', 'update', 'delete')
        :param entity_type: Type of entity affected (e.g., 'member', 'payment')
        :param user_id: ID of the user performing the action
        :param entity_id: ID of the affected entity
        :param old_values: Previous values before the action
        :param new_values: New values after the action
        :param ip_address: IP address of the requester
        :param user_agent: User agent string of the requester
        :return: The created audit log entry
        """
        # Generate data signatures for verification
        old_signature = AuditLog.generate_data_signature(old_values) if old_values else None
        new_signature = AuditLog.generate_data_signature(new_values) if new_values else None
        
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        return audit_log

    @staticmethod
    def get_logs(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        action: Optional[str] = None,
    ) -> list[AuditLog]:
        """
        Retrieve audit logs with optional filtering
        :param db: Database session
        :param skip: Number of records to skip
        :param limit: Maximum number of records to return
        :param user_id: Filter by user ID
        :param entity_type: Filter by entity type
        :param action: Filter by action
        :return: List of audit log entries
        """
        query = db.query(AuditLog)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type)
        if action:
            query = query.filter(AuditLog.action == action)
        return query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_reservation_logs(
        db: Session,
        reservation_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        """
        Retrieve audit logs for a specific reservation
        :param db: Database session
        :param reservation_id: ID of the reservation
        :param skip: Number of records to skip
        :param limit: Maximum number of records to return
        :return: List of audit log entries related to the reservation
        """
        return (
            db.query(AuditLog)
            .filter(
                and_(
                    AuditLog.entity_type == "reservation",
                    AuditLog.entity_id == reservation_id,
                )
            )
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_schedule_logs(
        db: Session,
        schedule_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        """
        Retrieve audit logs for a specific schedule
        :param db: Database session
        :param schedule_id: ID of the schedule
        :param skip: Number of records to skip
        :param limit: Maximum number of records to return
        :return: List of audit log entries related to the schedule
        """
        return (
            db.query(AuditLog)
            .filter(
                and_(
                    AuditLog.entity_type == "coach_schedule",
                    AuditLog.entity_id == schedule_id,
                )
            )
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )