from sqlalchemy import Column, Integer, String, Date, Boolean
from sqlalchemy.sql import expression
from sqlalchemy import DateTime
from .database import Base


class Member(Base):
    __tablename__ = 'members'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False, unique=True)
    join_date = Column(Date, nullable=False)
    membership_type = Column(String(20), nullable=False)
    is_deleted = Column(Boolean, server_default=expression.false(), nullable=False, default=False)
    deleted_by = Column(Integer, nullable=True)
    delete_reason = Column(String(100), nullable=True)
    deleted_at = Column(DateTime, nullable=True)