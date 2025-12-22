from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


class Member(Base):
    """会员数据模型"""
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    contact = Column(String(50), unique=True, index=True)
    level = Column(Integer, default=1)

    payments = relationship("Payment", back_populates="member")