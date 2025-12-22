from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from cryptography.fernet import Fernet
import os
from ..core.config import settings, ENCRYPTED_FIELDS, MEMBER_FIELDS

Base = declarative_base()

class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    phone_number = Column(String(20), nullable=False)
    id_card_number = Column(String(18), nullable=False)
    health_status = Column(Text, nullable=True)
    address = Column(String(200), nullable=True)
    email = Column(String(100), nullable=True)
    registration_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __init__(self, **kwargs):
        super(Member, self).__init__(**kwargs)
        self._encrypt_sensitive_fields()

    def _encrypt_sensitive_fields(self):
        cipher_suite = Fernet(settings.ENCRYPTION_KEY.encode())
        for field in ENCRYPTED_FIELDS:
            if hasattr(self, field):
                value = getattr(self, field)
                if value:
                    encrypted_value = cipher_suite.encrypt(value.encode())
                    setattr(self, field, encrypted_value.decode())

    def _decrypt_sensitive_fields(self):
        cipher_suite = Fernet(settings.ENCRYPTION_KEY.encode())
        for field in ENCRYPTED_FIELDS:
            if hasattr(self, field):
                value = getattr(self, field)
                if value:
                    decrypted_value = cipher_suite.decrypt(value.encode())
                    setattr(self, field, decrypted_value.decode())

    def to_dict(self, decrypt=False):
        data = {
            "id": self.id,
            "name": self.name,
            "phone_number": self.phone_number,
            "id_card_number": self.id_card_number,
            "health_status": self.health_status,
            "address": self.address,
            "email": self.email,
            "registration_date": self.registration_date.isoformat(),
            "last_updated": self.last_updated.isoformat()
        }
        if decrypt:
            self._decrypt_sensitive_fields()
            for field in ENCRYPTED_FIELDS:
                if field in data:
                    data[field] = getattr(self, field)
        return data

    def update_fields(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self._encrypt_sensitive_fields()
        self.last_updated = datetime.utcnow()

    def __repr__(self):
        return f"<Member(id={self.id}, name={self.name})>"
