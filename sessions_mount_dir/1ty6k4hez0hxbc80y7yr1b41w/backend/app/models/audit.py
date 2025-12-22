from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.models.coach import Coach
from .database import Base

class AuditLog(Base):
    """
    操作日志模型
    记录系统关键操作，用于审计追踪
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, comment="操作用户ID")
    action = Column(String(50), nullable=False, comment="操作类型")
    entity_type = Column(String(50), nullable=False, comment="操作实体类型")
    entity_id = Column(Integer, nullable=True, comment="操作实体ID")
    old_value = Column(Text, nullable=True, comment="旧值")
    new_value = Column(Text, nullable=True, comment="新值")
    ip_address = Column(String(50), nullable=True, comment="操作IP地址")
    user_agent = Column(String(255), nullable=True, comment="用户代理")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    related_coach_id = Column(Integer, ForeignKey('coaches.id'), nullable=True, comment="关联教练ID")

    @classmethod
    def create_log(cls, db, **kwargs):
        """
        创建审计日志的便捷方法
        :param db: 数据库会话
        :param kwargs: 日志属性
        :return: 创建的日志对象
        """
        try:
            log = cls(**kwargs)
            db.add(log)
            db.commit()
            db.refresh(log)
            return log
        except Exception as e:
            db.rollback()
            raise e