from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Index, Text

from sqlalchemy import Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base

class MemberStatus(enum.Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    EXPIRED = "expired"

class UserRole(enum.Enum):
    ADMIN = "admin"
    STAFF = "staff"
    MEMBER = "member"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.MEMBER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user")
    managed_members = relationship("Member", back_populates="manager")


class Member(Base):
    __tablename__ = "members"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    contact = Column(String(50), unique=True, nullable=False, index=True)
    level = Column(String(50), nullable=False)
    status = Column(Enum(MemberStatus), default=MemberStatus.ACTIVE, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    status_logs = relationship("MemberStatusLog", back_populates="member")
    entry_records = relationship("EntryRecord", back_populates="member")
    payments = relationship("Payment", back_populates="member")
    bookings = relationship("Booking", back_populates="member")
    manager = relationship("User", back_populates="managed_members")

class MemberStatusLog(Base):
    __tablename__ = "member_status_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    old_status = Column(Enum(MemberStatus))
    new_status = Column(Enum(MemberStatus), nullable=False)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    changed_by = Column(String(100))
    
    # Relationships
    member = relationship("Member", back_populates="status_logs")
    user = relationship("User", back_populates="audit_logs")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(100), nullable=False)
    table_name = Column(String(50), nullable=False)
    record_id = Column(Integer, nullable=False, index=True)
    old_values = Column(String)
    new_values = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    coach = Column(String(100), nullable=False)
    time = Column(DateTime(timezone=True), nullable=False)
    location = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    bookings = relationship("Booking", back_populates="course")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    member = relationship("Member", back_populates="payments")

class EntryRecord(Base):
    __tablename__ = "entry_records"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    entry_time = Column(DateTime(timezone=True), nullable=False)
    exit_time = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    member = relationship("Member", back_populates="entry_records")

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    member = relationship("Member", back_populates="payments")

class MemberMetadata(Base):
    __tablename__ = "member_metadata"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    key = Column(String(100), nullable=False, index=True)
    value = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    member = relationship("Member")

    # Indexes
    __table_args__ = (
        Index('idx_member_metadata_key_value', 'member_id', 'key'),
    )

class MemberDynamicData(Base):
    __tablename__ = "member_dynamic_data"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    data_type = Column(String(50), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    member = relationship("Member")

    # Indexes
    __table_args__ = (
        Index('idx_member_dynamic_type', 'member_id', 'data_type'),
    )
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    member = relationship("Member", back_populates="bookings")
    course = relationship("Course", back_populates="bookings")

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
class MemberDynamicData(Base):
    __tablename__ = "member_dynamic_data"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    data_type = Column(String(50), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    member = relationship("Member")

    # Indexes
    __table_args__ = (
        Index('idx_member_dynamic_type', 'member_id', 'data_type'),
    )

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    member = relationship("Member", back_populates="bookings")
    course = relationship("Course", back_populates="bookings")