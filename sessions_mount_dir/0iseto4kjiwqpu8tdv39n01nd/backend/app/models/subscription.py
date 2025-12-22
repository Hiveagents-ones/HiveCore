from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.models.order import Order


class SubscriptionPlanType(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(20), nullable=False, default=SubscriptionPlanType.MONTHLY)
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    duration_days = Column(Integer, nullable=False)
    features = Column(Text, nullable=True)  # JSON string of features
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    status = Column(String(20), nullable=False, default=SubscriptionStatus.PENDING)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    auto_renew = Column(Boolean, default=True)
    last_payment_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    last_payment = relationship("Order", foreign_keys=[last_payment_id])
    payment_history = relationship(
        "Order",
        foreign_keys="Order.subscription_id",
        back_populates="subscription"
    )

    def is_active(self) -> bool:
        return (
            self.status == SubscriptionStatus.ACTIVE and
            self.end_date > datetime.utcnow()
        )

    def days_remaining(self) -> int:
        if self.end_date <= datetime.utcnow():
            return 0
        delta = self.end_date - datetime.utcnow()
        return delta.days


class SubscriptionTransaction(Base):
    __tablename__ = "subscription_transactions"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    transaction_type = Column(String(20), nullable=False)  # "new", "renewal", "upgrade", "cancel"
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    payment_method = Column(String(50), nullable=False)
    transaction_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), nullable=False)  # "success", "failed", "pending"
    gateway_transaction_id = Column(String(100), nullable=True)
    gateway_response = Column(Text, nullable=True)  # JSON string of gateway response

    # Relationships
    subscription = relationship("Subscription")
    order = relationship("Order")
