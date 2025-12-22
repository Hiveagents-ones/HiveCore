from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


class Payment(Base):
    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey('members.id'))
    amount = Column(Float, nullable=False)
    payment_method = Column(String(50), nullable=False)
    transaction_id = Column(String(100), unique=True, nullable=False)
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    description = Column(String(255), nullable=True)

    member = relationship('Member', back_populates='payments')

    def __repr__(self):
        return f"<Payment {self.transaction_id} - {self.amount}>",


class MembershipCard(Base):
    __tablename__ = 'membership_cards'

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey('members.id'))
    card_type = Column(String(50), nullable=False)
    balance = Column(Float, default=0.0)
    expiry_date = Column(DateTime, nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    member = relationship('Member', back_populates='membership_cards')

    def __repr__(self):
        return f"<MembershipCard {self.card_type} - {self.balance}>",


class BillingRecord(Base):
    __tablename__ = 'billing_records'

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey('members.id'))
    amount = Column(Float, nullable=False)
    billing_type = Column(String(50), nullable=False)
    billing_cycle = Column(String(20), nullable=False)
    status = Column(String(20), default='pending')
    due_date = Column(DateTime, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    member = relationship('Member', back_populates='billing_records')

    def __repr__(self):
        return f"<BillingRecord {self.billing_type} - {self.amount}>",