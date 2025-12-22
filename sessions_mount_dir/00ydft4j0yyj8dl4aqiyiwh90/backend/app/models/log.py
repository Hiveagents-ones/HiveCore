from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from .database import Base


class OperationLog(Base):
    """
    操作日志数据模型
    记录系统关键操作日志，用于审计和追踪
    """
    __tablename__ = 'operation_logs'

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey('members.id'), nullable=True, comment='关联会员ID')
    action = Column(String(50), nullable=False, comment='操作类型')
    entity_type = Column(String(50), nullable=True, comment='操作实体类型')
    entity_id = Column(Integer, nullable=True, comment='操作实体ID')
    details = Column(String(500), nullable=True, comment='操作详情')
    ip_address = Column(String(50), nullable=True, comment='操作IP地址')
    user_agent = Column(String(200), nullable=True, comment='用户代理')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment='创建时间')

    def __repr__(self):
        return f"<OperationLog(id={self.id}, action='{self.action}')>"


class SystemLog(Base):
    """
    系统日志数据模型
    记录系统运行日志
    """
    __tablename__ = 'system_logs'

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20), nullable=False, comment='日志级别')
    module = Column(String(50), nullable=False, comment='模块名称')
    message = Column(String(500), nullable=False, comment='日志消息')
    stack_trace = Column(String(2000), nullable=True, comment='堆栈跟踪')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment='创建时间')

    def __repr__(self):
        return f"<SystemLog(id={self.id}, level='{self.level}', module='{self.module}')>"