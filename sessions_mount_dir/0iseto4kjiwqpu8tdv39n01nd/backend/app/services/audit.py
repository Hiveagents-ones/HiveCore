import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)

class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def log_action(
        self,
        user_id: int,
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        记录审计日志
        
        Args:
            user_id: 操作用户ID
            action: 操作类型 (create, update, delete, view)
            resource_type: 资源类型 (member, profile, etc.)
            resource_id: 资源ID
            details: 操作详情
            ip_address: 客户端IP
            user_agent: 客户端User-Agent
            
        Returns:
            AuditLog: 创建的审计日志记录
        """
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
                timestamp=datetime.utcnow(),
            )
            
            self.db.add(audit_log)
            self.db.commit()
            self.db.refresh(audit_log)
            
            # 检查是否需要发送告警
            self._check_and_send_alert(audit_log)
            
            return audit_log
            
        except Exception as e:
            logger.error(f"Failed to log audit action: {str(e)}")
            self.db.rollback()
            raise

    def _check_and_send_alert(self, audit_log: AuditLog) -> None:
        """
        检查是否需要发送告警并发送
        
        Args:
            audit_log: 审计日志记录
        """
        # 定义需要告警的操作类型
        alert_actions = {
            "delete": "删除操作",
            "update": "敏感信息更新",
            "create": "高风险创建",
        }
        
        # 定义需要告警的资源类型
        alert_resources = {
            "member": "会员信息",
            "profile": "个人资料",
            "payment": "支付信息",
            "coach": "教练信息",
        }
        
        if audit_log.action in alert_actions and audit_log.resource_type in alert_resources:
            alert_message = (
                f"安全告警: 用户 {audit_log.user_id} 执行了 {alert_actions[audit_log.action]} "
                f"操作，涉及 {alert_resources[audit_log.resource_type]}"
            )
            
            if audit_log.resource_id:
                alert_message += f" (ID: {audit_log.resource_id})"
            
            self._send_alert(alert_message, audit_log)

    def _send_alert(self, message: str, audit_log: AuditLog) -> None:
        """
        发送告警
        
        Args:
            message: 告警消息
            audit_log: 相关的审计日志
        """
        try:
            # 这里可以集成实际的告警系统，如邮件、短信、Slack等
            # 目前只是记录日志
            logger.warning(f"ALERT: {message}")
            
            # 示例: 可以在这里添加邮件发送逻辑
            # if settings.ALERT_EMAIL_ENABLED:
            #     send_email_alert(message, audit_log)
            
            # 示例: 可以在这里添加Slack通知逻辑
            # if settings.SLACK_WEBHOOK_URL:
            #     send_slack_alert(message, audit_log)
            
        except Exception as e:
            logger.error(f"Failed to send alert: {str(e)}")

    def get_audit_logs(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """
        获取审计日志
        
        Args:
            user_id: 用户ID过滤
            action: 操作类型过滤
            resource_type: 资源类型过滤
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回记录数限制
            offset: 偏移量
            
        Returns:
            list[AuditLog]: 审计日志列表
        """
        query = self.db.query(AuditLog)
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)
            
        return query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    def get_audit_log_count(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """
        获取审计日志总数
        
        Args:
            user_id: 用户ID过滤
            action: 操作类型过滤
            resource_type: 资源类型过滤
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            int: 审计日志总数
        """
        query = self.db.query(AuditLog)
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)
            
        return query.count()
