from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


class Payment(Base):
    """支付结算数据模型"""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    amount = Column(Float, CheckConstraint('amount > 0'), nullable=False)
    payment_date = Column(DateTime, default=datetime.utcnow)
    payment_method = Column(String(50), CheckConstraint("payment_method IN ('cash', 'credit_card', 'wechat', 'alipay')"), nullable=False)

    member = relationship("Member", back_populates="payments")
    __table_args__ = (
        CheckConstraint('payment_date <= CURRENT_TIMESTAMP', name='check_payment_date'),
    )

    def __repr__(self):
        return f"<Payment(id={self.id}, member_id={self.member_id}, amount={self.amount})>"