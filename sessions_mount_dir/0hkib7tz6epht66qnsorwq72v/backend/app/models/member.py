from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="会员姓名")
    phone = Column(String(20), unique=True, index=True, nullable=False, comment="手机号码")
    email = Column(String(100), unique=True, index=True, nullable=True, comment="电子邮箱")
    level = Column(String(20), default="普通会员", nullable=False, comment="会员等级")
    points = Column(Integer, default=0, nullable=False, comment="会员积分")
    remaining_membership = Column(Integer, default=0, nullable=False, comment="剩余会籍(月)")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    notes = Column(Text, nullable=True, comment="备注信息")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<Member(id={self.id}, name='{self.name}', phone='{self.phone}')>"
