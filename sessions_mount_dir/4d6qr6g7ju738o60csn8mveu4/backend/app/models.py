from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.security import encrypt_sensitive_data, decrypt_sensitive_data

Base = declarative_base()

class MembershipType(Base):
    """
    会员卡类型模型
    支持动态配置不同类型的会员卡（如月卡、季卡、年卡等）
    """
    __tablename__ = 'membership_types'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, comment='会员卡类型名称')
    description = Column(Text, nullable=True, comment='会员卡类型描述')
    duration_months = Column(Integer, nullable=False, comment='有效期限（月）')
    price = Column(Integer, nullable=False, comment='价格（分）')
    is_active = Column(Boolean, default=True, comment='是否启用')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    # 关联会员
    members = relationship('Member', back_populates='membership_type')

class Member(Base):
    """
    会员模型
    存储会员基本信息，包括加密存储的身份证号
    """
    __tablename__ = 'members'

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(String(20), unique=True, nullable=False, index=True, comment='会员唯一ID')
    name = Column(String(50), nullable=False, comment='姓名')
    phone = Column(String(20), unique=True, nullable=False, index=True, comment='手机号')
    id_card_encrypted = Column(String(255), nullable=False, comment='加密后的身份证号')
    membership_type_id = Column(Integer, ForeignKey('membership_types.id'), nullable=False, comment='会员卡类型ID')
    start_date = Column(DateTime, nullable=False, comment='会员开始日期')
    end_date = Column(DateTime, nullable=False, comment='会员结束日期')
    is_active = Column(Boolean, default=True, comment='会员状态')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    # 关联会员卡类型
    membership_type = relationship('MembershipType', back_populates='members')

    @property
    def id_card(self):
        """
        获取解密后的身份证号
        """
        return decrypt_sensitive_data(self.id_card_encrypted)

    @id_card.setter
    def id_card(self, value):
        """
        设置身份证号时自动加密存储
        """
        self.id_card_encrypted = encrypt_sensitive_data(value)

    def __repr__(self):
        return f"<Member(member_id='{self.member_id}', name='{self.name}', phone='{self.phone}')>"
