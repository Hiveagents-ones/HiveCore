from sqlalchemy import Column, Integer, String, Date, Enum
from sqlalchemy.ext.declarative import declarative_base
from .database import Base


# 定义会员类型枚举
class MemberType(str, Enum):
    REGULAR = 'regular'
    PREMIUM = 'premium'


# 会员数据模型
class Member(Base):
    __tablename__ = 'members'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    contact = Column(String, index=True)
    member_type = Column(Enum(MemberType), default=MemberType.REGULAR)
    valid_until = Column(Date)

    def __repr__(self):
        return f'<Member {self.name} ({self.member_type}) valid until {self.valid_until}>'