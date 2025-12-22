from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_date = Column(DateTime, default=datetime.utcnow)
    payment_method = Column(String(50), nullable=False)
    invoice_number = Column(String(50), unique=True)
    status = Column(String(20), default="pending", comment="支付状态: pending/processing/completed/failed/refunded")
    transaction_id = Column(String(100), unique=True)
    channel = Column(String(50), comment="支付渠道: wechat/alipay/unionpay/cash/bank_transfer")
    notes = Column(String(500))
    currency = Column(String(3), default="CNY", comment="货币类型: CNY/USD/EUR")

    member = relationship("Member", back_populates="payments")

    def __repr__(self):
        return f"<Payment(id={self.id}, amount={self.amount}, method={self.payment_method})>"


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)
    invoice_number = Column(String(50), unique=True, nullable=False)
    issue_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime)
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, nullable=False)
    status = Column(String(20), default="unpaid")
    pdf_path = Column(String(255))

    payment = relationship("Payment", back_populates="invoice")

    def __repr__(self):
        return f"<Invoice(id={self.id}, number={self.invoice_number})>"


Payment.invoice = relationship("Invoice", back_populates="payment", uselist=False)