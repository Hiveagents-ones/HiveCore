from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Member(Base):
    __tablename__ = "members"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True)
    birthday = Column(DateTime)
    gender = Column(String(10))  # 'male', 'female', 'other'
    address = Column(Text)
    total_spent = Column(Float, default=0.0)
    visit_count = Column(Integer, default=0)
    last_visit = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False)
    shop = relationship("Shop", back_populates="members")
    tags = relationship("MemberTag", back_populates="member", cascade="all, delete-orphan")
    notes = relationship("MemberNote", back_populates="member", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="member")
    consumptions = relationship("Consumption", back_populates="member")

class MemberTag(Base):
    __tablename__ = "member_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    color = Column(String(7))  # Hex color code
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    member = relationship("Member", back_populates="tags")
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False)
    shop = relationship("Shop")

class MemberNote(Base):
    __tablename__ = "member_notes"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    member = relationship("Member", back_populates="notes")
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=False)
    staff = relationship("Staff")
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False)
    shop = relationship("Shop")

class Consumption(Base):
    __tablename__ = "consumptions"
    
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    description = Column(Text)
    payment_method = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    member = relationship("Member", back_populates="consumptions")
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False)
    shop = relationship("Shop")
    staff_id = Column(Integer, ForeignKey("staff.id"))
    staff = relationship("Staff")
    service_id = Column(Integer, ForeignKey("services.id"))
    service = relationship("Service")

class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    appointment_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), default="scheduled")  # scheduled, completed, cancelled, no_show
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    member = relationship("Member", back_populates="appointments")
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False)
    shop = relationship("Shop")
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=False)
    staff = relationship("Staff")
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    service = relationship("Service")