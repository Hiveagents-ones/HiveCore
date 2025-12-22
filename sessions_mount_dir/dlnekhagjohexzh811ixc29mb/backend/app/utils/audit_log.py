from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.members import AuditLogCreate

class AuditLogger:
    """
    审计日志工具类，用于记录系统中的关键操作
    """
    
    @staticmethod
    def log_action(
        db: Session,
        action: str,
        entity_type: str,
        entity_id: int,
        performed_by: str,
        details: Optional[str] = None
    ) -> None:
        """
        记录审计日志
        
        Args:
            db: 数据库会话
            action: 执行的操作 (create/update/delete)
            entity_type: 实体类型 (member/course/coach/payment)
            entity_id: 实体ID
            performed_by: 操作执行者
            details: 操作详情 (可选)
        """
        audit_log = AuditLogCreate(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            performed_by=performed_by,
            details=details,
            timestamp=datetime.utcnow()
        )
        
        db.add(audit_log)
        db.commit()
        
    @staticmethod
    def log_member_action(
    @staticmethod
    def log_payment_action(
        db: Session,
        action: str,
        payment_id: int,
        performed_by: str,
        details: Optional[str] = None
    ) -> None:
        """
        记录支付相关操作的审计日志

        Args:
            db: 数据库会话
            action: 执行的操作 (create/update/delete)
            payment_id: 支付记录ID
            performed_by: 操作执行者
            details: 操作详情 (可选)
        """
        AuditLogger.log_action(
            db=db,
            action=action,
            entity_type="payment",
            entity_id=payment_id,
            performed_by=performed_by,
            details=details
        )
        db: Session,
        action: str,
        member_id: int,
        performed_by: str,
        details: Optional[str] = None
    ) -> None:
        """
        记录会员相关操作的审计日志
        
        Args:
            db: 数据库会话
            action: 执行的操作 (create/update/delete)
            member_id: 会员ID
            performed_by: 操作执行者
            details: 操作详情 (可选)
        """
        AuditLogger.log_action(
            db=db,
            action=action,
            entity_type="member",
            entity_id=member_id,
            performed_by=performed_by,
            details=details
        )

    @staticmethod
    def get_logs_for_entity(
        db: Session,
        entity_type: str,
        entity_id: int,
        limit: int = 100
    ) -> list:
        """
        获取指定实体的审计日志
        
        Args:
            db: 数据库会话
            entity_type: 实体类型
            entity_id: 实体ID
            limit: 返回的最大记录数
            
        Returns:
            审计日志列表
        """
        return db.query(AuditLog).filter(
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == entity_id
        ).order_by(
            AuditLog.timestamp.desc()
        ).limit(limit).all()