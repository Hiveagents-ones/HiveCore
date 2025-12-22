from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine, EncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import StringEncryptedType
from sqlalchemy_utils.types.json import JSONType
from sqlalchemy_utils.types.encrypted.encrypted_type import FernetEngine
from sqlalchemy.orm import relationship
from .database import Base
from backend.app.database import SECRET_KEY, ENCRYPTION_PAD_LENGTH


class Member(Base):
    """会员数据模型"""
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    version_id = Column(Integer, nullable=False, default=0)  # 乐观锁版本控制
    name = Column(String(50), nullable=False)
    phone = Column(StringEncryptedType(String(20), SECRET_KEY, FernetEngine, padding='pkcs5', max_length=20+ENCRYPTION_PAD_LENGTH), nullable=False, unique=True, index=True)
    email = Column(StringEncryptedType(String(100), SECRET_KEY, FernetEngine, padding='pkcs5', max_length=100+ENCRYPTION_PAD_LENGTH), nullable=False, unique=True, index=True)
    join_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    level = Column(Integer, nullable=False, default=1)  # 会员等级 1-5
    discount_rate = Column(Integer, nullable=False, default=100)  # 折扣率百分比(100表示无折扣)
    
    # 关系定义
    bookings = relationship("Booking", back_populates="member")
    payments = relationship("Payment", back_populates="member")
    audit_logs = relationship("AuditLog", back_populates="member")
    __mapper_args__ = {
        "version_id_col": version_id,
        "version_id_generator": False
    }

    def __repr__(self):
        return f"<Member(id={self.id}, name='{self.name}', phone='{self.phone}', level={self.level}, discount_rate={self.discount_rate})>"


class MemberCreate:
    """会员创建模型"""
    name: str
    phone: str
    email: str
    join_date: Optional[datetime] = None
    level: Optional[int] = 1
    discount_rate: Optional[int] = 100


class MemberUpdate:
    version_id: Optional[int] = None
    """会员更新模型"""
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    level: Optional[int] = None
    discount_rate: Optional[int] = None


class AuditLog(Base):
    """会员操作审计日志"""
    __tablename__ = "member_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    action = Column(String(50), nullable=False)  # create/update/delete
    changed_fields = Column(JSONType)  # JSON of changed fields
    operator_id = Column(Integer)  # staff who performed the action
    operation_time = Column(DateTime, nullable=False, default=datetime.utcnow)

    # 关系定义
    member = relationship("Member", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, member_id={self.member_id}, action='{self.action}')>"