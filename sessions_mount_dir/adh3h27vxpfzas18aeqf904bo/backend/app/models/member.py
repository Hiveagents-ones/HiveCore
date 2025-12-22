from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from .database import Base


class Member(Base):
    """会员数据模型"""
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, comment="会员姓名")
    phone = Column(String(20), unique=True, index=True, nullable=False, comment="手机号码")
    email = Column(String(100), unique=True, index=True, nullable=True, comment="电子邮箱")
    card_status = Column(Boolean, default=True, comment="会员卡状态(True=有效)")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<Member(id={self.id}, name='{self.name}', phone='{self.phone}')>"