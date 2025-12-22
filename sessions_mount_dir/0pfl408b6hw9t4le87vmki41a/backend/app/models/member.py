from datetime import datetime, date
from typing import Optional

from sqlalchemy import Column, Integer, String, Date, Boolean, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

class MemberLevel(enum.Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"

class HealthStatus(enum.Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"

class Member(Base):
    """
    会员数据模型
    """
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    phone = Column(String(20), nullable=False, unique=True, index=True)
    email = Column(String(100), nullable=True, unique=True, index=True)
    member_level = Column(SQLEnum(MemberLevel), nullable=False, default=MemberLevel.BRONZE)
    join_date = Column(Date, nullable=False, default=date.today)
    expiry_date = Column(Date, nullable=False)
    health_status = Column(SQLEnum(HealthStatus), nullable=True, default=HealthStatus.GOOD)
    health_notes = Column(Text, nullable=True)
    emergency_contact = Column(String(100), nullable=True)
    emergency_phone = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    bookings = relationship("Booking", back_populates="member")
    payments = relationship("Payment", back_populates="member")

    def __repr__(self):
        return f"<Member(id={self.id}, name='{self.name}', level='{self.member_level.value}')>"

    @property
    def is_membership_valid(self) -> bool:
        """检查会员资格是否有效"""
        return self.expiry_date >= date.today() and self.is_active

    def to_dict(self):
        """将会员对象转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "member_level": self.member_level.value,
            "join_date": self.join_date.isoformat() if self.join_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "health_status": self.health_status.value if self.health_status else None,
            "health_notes": self.health_notes,
            "emergency_contact": self.emergency_contact,
            "emergency_phone": self.emergency_phone,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_membership_valid": self.is_membership_valid
        }
