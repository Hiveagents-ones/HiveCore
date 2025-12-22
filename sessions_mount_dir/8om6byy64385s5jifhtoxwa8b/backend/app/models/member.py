from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from cryptography.fernet import Fernet
import os

Base = declarative_base()

# 加密密钥（实际项目中应从环境变量或配置文件中获取）
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key())
cipher_suite = Fernet(ENCRYPTION_KEY)

class Member(Base):
    __tablename__ = 'members'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    email = Column(String(100), nullable=True, index=True)
    member_card_number = Column(String(50), unique=True, nullable=False, index=True)
    member_level = Column(String(20), nullable=False, default='basic')
    remaining_sessions = Column(Integer, default=0)
    expiry_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 加密字段
    encrypted_data = Column(String(500), nullable=True)

    # 索引优化
    __table_args__ = (
        Index('idx_member_level_active', 'member_level', 'is_active'),
        Index('idx_phone_active', 'phone', 'is_active'),
        Index('idx_card_number_level', 'member_card_number', 'member_level'),
    )

    def encrypt_sensitive_data(self, data: str) -> str:
        """加密敏感数据"""
        if not data:
            return ''
        return cipher_suite.encrypt(data.encode()).decode()

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """解密敏感数据"""
        if not encrypted_data:
            return ''
        return cipher_suite.decrypt(encrypted_data.encode()).decode()

    def set_encrypted_data(self, data: dict):
        """设置加密数据"""
        import json
        json_data = json.dumps(data)
        self.encrypted_data = self.encrypt_sensitive_data(json_data)

    def get_encrypted_data(self) -> dict:
        """获取解密后的数据"""
        import json
        if not self.encrypted_data:
            return {}
        decrypted_json = self.decrypt_sensitive_data(self.encrypted_data)
        return json.loads(decrypted_json)

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'member_card_number': self.member_card_number,
            'member_level': self.member_level,
            'remaining_sessions': self.remaining_sessions,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
