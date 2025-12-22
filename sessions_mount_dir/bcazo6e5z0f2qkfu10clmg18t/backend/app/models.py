from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    id_card = Column(String(18), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    address = Column(String(255), nullable=True)
    registration_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(Boolean, default=True, nullable=False)  # True: active, False: inactive
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_member_phone', 'phone'),
        Index('idx_member_id_card', 'id_card'),
        Index('idx_member_email', 'email'),
        Index('idx_member_status', 'status'),
    )

    def __repr__(self):
        return f"<Member(id={self.id}, member_id={self.member_id}, name={self.name})>"
