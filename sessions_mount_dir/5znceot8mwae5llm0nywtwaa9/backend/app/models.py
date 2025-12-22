from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from cryptography.fernet import Fernet
import os

Base = declarative_base()

# Encryption key should be stored securely, e.g., in environment variables
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key().decode())
cipher_suite = Fernet(ENCRYPTION_KEY.encode())

class Member(Base):
    __tablename__ = 'members'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    id_card = Column(String(18), unique=True, nullable=False, index=True)
    membership_plan = Column(String(50), nullable=False)
    account_number = Column(String(20), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    notes = Column(Text, nullable=True)

    def encrypt_sensitive_data(self, data):
        """Encrypt sensitive data before storing"""
        return cipher_suite.encrypt(data.encode()).decode()

    def decrypt_sensitive_data(self, encrypted_data):
        """Decrypt sensitive data when retrieving"""
        return cipher_suite.decrypt(encrypted_data.encode()).decode()

    def set_phone(self, phone):
        """Set encrypted phone number"""
        self.phone = self.encrypt_sensitive_data(phone)

    def get_phone(self):
        """Get decrypted phone number"""
        return self.decrypt_sensitive_data(self.phone)

    def set_id_card(self, id_card):
        """Set encrypted ID card number"""
        self.id_card = self.encrypt_sensitive_data(id_card)

    def get_id_card(self):
        """Get decrypted ID card number"""
        return self.decrypt_sensitive_data(self.id_card)

    def generate_account_number(self):
        """Generate unique account number"""
        import random
        import string
        while True:
            account = 'MB' + ''.join(random.choices(string.digits, k=8))
            if not Member.query.filter_by(account_number=account).first():
                return account

    def __repr__(self):
        return f"<Member(id={self.id}, name={self.name}, account={self.account_number})>"
