"""Member database models.

This module contains SQLAlchemy models for member management.
"""

import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Member(Base):
    """Member model.

    Attributes:
        id: Primary key
        phone: Member phone number (unique)
        name: Member name
        validity_start: Membership validity start date
        validity_end: Membership validity end date
        created_at: Record creation timestamp
        updated_at: Record update timestamp
    """

    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    validity_start: Mapped[datetime.date] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow
    )
    validity_end: Mapped[datetime.date] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    @property
    def is_active(self) -> bool:
        """Check if membership is currently valid.

        Returns:
            bool: True if membership is valid, False otherwise
        """
        now = datetime.datetime.utcnow()
        return self.validity_start <= now <= self.validity_end

    @property
    def is_expired(self) -> bool:
        """Check if membership has expired.

        Returns:
            bool: True if membership is expired, False otherwise
        """
        return datetime.datetime.utcnow() > self.validity_end

    def __repr__(self) -> str:
        """String representation of Member.

        Returns:
            str: String representation
        """
        return f"<Member(id={self.id}, phone={self.phone}, name={self.name})>"


class RenewalRecord(Base):
    """Renewal record model.

    Tracks membership renewal transactions.

    Attributes:
        id: Primary key
        member_id: Foreign key to member
        previous_end: Previous validity end date
        new_end: New validity end date after renewal
        days_added: Number of days added
        payment_status: Payment transaction status
        amount: Renewal amount
        created_at: Record creation timestamp
    """

    __tablename__ = "renewal_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    previous_end: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    new_end: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    days_added: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, completed, failed
    amount: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    def __repr__(self) -> str:
        """String representation of RenewalRecord.

        Returns:
            str: String representation
        """
        return f"<RenewalRecord(id={self.id}, member_id={self.member_id}, days_added={self.days_added})>"
