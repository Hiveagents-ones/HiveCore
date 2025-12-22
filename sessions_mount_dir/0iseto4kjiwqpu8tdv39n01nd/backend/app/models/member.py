from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.security import encrypt_data, decrypt_data
from ..core.database import Base

class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    encrypted_phone = Column(Text, nullable=True)
    membership_level = Column(String(50), default="basic")
    remaining_membership = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Audit log relationship
    audit_logs = relationship("AuditLog", back_populates="member")

    def set_phone(self, phone: str):
        """Encrypt and set phone number"""
        self.phone = phone
        self.encrypted_phone = encrypt_data(phone) if phone else None

    def get_phone(self) -> str:
        """Decrypt and return phone number"""
        return decrypt_data(self.encrypted_phone) if self.encrypted_phone else self.phone

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    action = Column(String(100), nullable=False)
    old_values = Column(Text, nullable=True)
    new_values = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Member relationship
    member = relationship("Member", back_populates="audit_logs")
