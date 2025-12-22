from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Member(Base):
    __tablename__ = 'members'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    membership_level = Column(String(50), default='basic')
    remaining_membership = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Audit fields
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    updated_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Relationships
    creator = relationship('User', foreign_keys=[created_by], back_populates='created_members')
    updater = relationship('User', foreign_keys=[updated_by], back_populates='updated_members')
    
    def calculate_membership_expiry(self):
        """Calculate membership expiry date based on remaining membership days"""
        if self.remaining_membership <= 0:
            return None
        return datetime.utcnow() + timedelta(days=self.remaining_membership)
    
    def extend_membership(self, days: float, operator_id: int):
        """Extend membership by specified number of days"""
        self.remaining_membership += days
        self.updated_by = operator_id
        self.updated_at = datetime.utcnow()
    
    def consume_membership(self, days: float, operator_id: int):
        """Consume membership days"""
        if self.remaining_membership >= days:
            self.remaining_membership -= days
            self.updated_by = operator_id
            self.updated_at = datetime.utcnow()
            return True
        return False
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'membership_level': self.membership_level,
            'remaining_membership': self.remaining_membership,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'membership_expiry': self.calculate_membership_expiry().isoformat() if self.calculate_membership_expiry() else None
        }