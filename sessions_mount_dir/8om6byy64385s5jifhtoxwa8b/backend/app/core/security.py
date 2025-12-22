from datetime import datetime, timedelta
from typing import Any, Union, Optional

from jose import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from cryptography.fernet import Fernet
import ssl

from backend.app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


class DataEncryption:
    """数据加密工具类"""
    
    def __init__(self, key: Optional[bytes] = None):
        if key:
            self.cipher_suite = Fernet(key)
        else:
            self.cipher_suite = Fernet(settings.ENCRYPTION_KEY.encode())
    
    def encrypt(self, data: str) -> str:
        """加密字符串数据"""
        if not data:
            return data
        encrypted_data = self.cipher_suite.encrypt(data.encode())
        return encrypted_data.decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """解密字符串数据"""
        if not encrypted_data:
            return encrypted_data
        try:
            decrypted_data = self.cipher_suite.decrypt(encrypted_data.encode())
            return decrypted_data.decode()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid encrypted data"
            )


class HTTPSConfig:
    """HTTPS配置工具类"""
    
    @staticmethod
    def create_ssl_context(certfile: str, keyfile: str) -> ssl.SSLContext:
        """创建SSL上下文"""
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        try:
            context.load_cert_chain(certfile=certfile, keyfile=keyfile)
            return context
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load SSL certificate: {str(e)}"
            )
    
    @staticmethod
    def get_ssl_protocol_version() -> int:
        """获取推荐的SSL协议版本"""
        return ssl.TLSVersion.TLSv1_2


# 全局加密实例
encryption = DataEncryption()
