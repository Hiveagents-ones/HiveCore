import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from ..models.member import Member
from ..models.booking import Booking

Base = declarative_base()

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, action={self.action})>"

class AuditService:
    def __init__(self, db_session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)
    
    def log_member_action(self, 
                         user_id: int, 
                         action: str, 
                         member_id: Optional[int] = None,
                         details: Optional[Dict[str, Any]] = None,
                         ip_address: Optional[str] = None) -> None:
        """
        记录会员相关操作的审计日志
        
        Args:
            user_id: 操作用户ID
            action: 操作类型 (create, update, delete, view, etc.)
            member_id: 被操作的会员ID
            details: 操作详情字典
            ip_address: 操作来源IP地址
        """
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type='member',
                resource_id=member_id,
                details=str(details) if details else None,
                ip_address=ip_address
            )
            
            self.db_session.add(audit_log)
            self.db_session.commit()
            
            self.logger.info(f"Audit log created: {audit_log}")
        except Exception as e:
            self.logger.error(f"Failed to create audit log: {str(e)}")
            self.db_session.rollback()

    def log_booking_action(self,
                         user_id: int,
                         action: str,
                         booking_id: Optional[int] = None,
                         details: Optional[Dict[str, Any]] = None,
                         ip_address: Optional[str] = None) -> None:
        """
        记录预约相关操作的审计日志

        Args:
            user_id: 操作用户ID
            action: 操作类型 (create, update, cancel, view, etc.)
            booking_id: 被操作的预约ID
            details: 操作详情字典
            ip_address: 操作来源IP地址
        """
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type='booking',
                resource_id=booking_id,
                details=str(details) if details else None,
                ip_address=ip_address
            )

            self.db_session.add(audit_log)
            self.db_session.commit()

            self.logger.info(f"Booking audit log created: {audit_log}")
        except Exception as e:
            self.logger.error(f"Failed to create booking audit log: {str(e)}")
            self.db_session.rollback()

    def get_booking_audit_logs(self, booking_id: int, limit: int = 100) -> list:
        """
        获取特定预约的审计日志

        Args:
            booking_id: 预约ID
            limit: 返回记录数限制

        Returns:
            list: 审计日志列表
        """
        try:
            logs = self.db_session.query(AuditLog)\
                .filter(AuditLog.resource_type == 'booking')\
                .filter(AuditLog.resource_id == booking_id)\
                .order_by(AuditLog.timestamp.desc())\
                .limit(limit)\
                .all()
            return logs
        except Exception as e:
            self.logger.error(f"Failed to retrieve audit logs for booking {booking_id}: {str(e)}")
            return []
    
    def get_member_audit_logs(self, member_id: int, limit: int = 100) -> list:
        """
        获取特定会员的审计日志
        
        Args:
            member_id: 会员ID
            limit: 返回记录数限制
            
        Returns:
            list: 审计日志列表
        """
        try:
            logs = self.db_session.query(AuditLog)\
                .filter(AuditLog.resource_type == 'member')\
                .filter(AuditLog.resource_id == member_id)\
                .order_by(AuditLog.timestamp.desc())\
                .limit(limit)\
                .all()
            return logs
        except Exception as e:
            self.logger.error(f"Failed to retrieve audit logs for member {member_id}: {str(e)}")
            return []
    
    def get_user_audit_logs(self, user_id: int, limit: int = 100) -> list:
        """
        获取特定用户的所有审计日志
        
        Args:
            user_id: 用户ID
            limit: 返回记录数限制
            
        Returns:
            list: 审计日志列表
        """
        try:
            logs = self.db_session.query(AuditLog)\
                .filter(AuditLog.user_id == user_id)\
                .order_by(AuditLog.timestamp.desc())\
                .limit(limit)\
                .all()
            return logs
        except Exception as e:
            self.logger.error(f"Failed to retrieve audit logs for user {user_id}: {str(e)}")
            return []
    
    def log_system_action(self, 
                         user_id: int, 
                         action: str, 
                         resource_type: str,
                         resource_id: Optional[int] = None,
                         details: Optional[Dict[str, Any]] = None,
                         ip_address: Optional[str] = None) -> None:
        """
        记录系统级操作的审计日志
        
        Args:
            user_id: 操作用户ID
            action: 操作类型
            resource_type: 资源类型
            resource_id: 资源ID
            details: 操作详情字典
            ip_address: 操作来源IP地址
        """
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=str(details) if details else None,
                ip_address=ip_address
            )
            
            self.db_session.add(audit_log)
            self.db_session.commit()
            
            self.logger.info(f"System audit log created: {audit_log}")
        except Exception as e:
            self.logger.error(f"Failed to create system audit log: {str(e)}")
            self.db_session.rollback()
