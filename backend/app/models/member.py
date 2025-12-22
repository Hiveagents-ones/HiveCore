from sqlalchemy import Column, Integer, String, Text
from ..database import Base

class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    phone = Column(String, nullable=False)
    goal = Column(Text, nullable=False)
class MemberCard(Base):
    __tablename__ = "member_cards"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    card_type = Column(String, nullable=False)
    expiry_date = Column(String, nullable=False)
    status = Column(String, nullable=False, default="inactive")

    member = relationship("Member", back_populates="cards")

Member.cards = relationship("MemberCard", order_by=MemberCard.id, back_populates="member")