import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import Request

logger = logging.getLogger(__name__)


class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, db: Session):
        self.db = db
        
    def log_action(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """记录审计日志
        
        Args:
            action: 操作类型 (create, update, delete, view, login, logout等)
            resource_type: 资源类型 (member, course, order等)
            resource_id: 资源ID
            user_id: 操作用户ID
            details: 操作详情
            ip_address: 客户端IP地址
            user_agent: 用户代理信息
        """
        try:
            audit_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "user_id": user_id,
                "details": details or {},
                "ip_address": ip_address,
                "user_agent": user_agent
            }
            
            # 记录到日志文件
            logger.info(f"AUDIT: {audit_data}")
            
            # TODO: 这里可以扩展为保存到数据库的审计日志表
            # from app.models.audit import AuditLog
            # audit_log = AuditLog(**audit_data)
            # self.db.add(audit_log)
            # self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log audit action: {str(e)}")
            
    def log_member_action(
        self,
        action: str,
        member_id: str,
        user_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ) -> None:
        """记录会员相关操作的审计日志
        
        Args:
            action: 操作类型 (register, update, delete, view等)
            member_id: 会员ID
            user_id: 操作用户ID
            changes: 变更内容
            request: FastAPI请求对象
        """
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            
        self.log_action(
            action=action,
            resource_type="member",
            resource_id=member_id,
            user_id=user_id,
            details=changes,
            ip_address=ip_address,
            user_agent=user_agent
        )


def get_audit_logger(db: Session) -> AuditLogger:
    """获取审计日志记录器实例"""
    return AuditLogger(db)
