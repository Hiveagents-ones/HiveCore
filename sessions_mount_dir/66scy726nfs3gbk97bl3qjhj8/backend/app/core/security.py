from datetime import datetime, timedelta
from typing import Any, Union, Optional

from jose import jwt, JWTError
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import base64
import hashlib

from .config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Field encryption context
# Ensure the encryption key is 32 bytes long for Fernet
key = base64.urlsafe_b64encode(settings.ENCRYPTION_KEY.encode()[:32].ljust(32, b'0'))
cipher_suite = Fernet(key)


def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """
    Verify a JWT token and return the subject (user ID).
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except JWTError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password.
    """
    return pwd_context.hash(password)


def encrypt_field(value: str) -> str:
    """
    Encrypt a sensitive field value.
    """
    if not isinstance(value, str):
        value = str(value)
    encrypted_value = cipher_suite.encrypt(value.encode())
    return encrypted_value.decode()


def decrypt_field(encrypted_value: str) -> str:
    """
    Decrypt a sensitive field value.
    """
    if not isinstance(encrypted_value, str):
        encrypted_value = str(encrypted_value)
    decrypted_value = cipher_suite.decrypt(encrypted_value.encode())
    return decrypted_value.decode()


def generate_hash(data: str) -> str:
    """
    Generate a SHA-256 hash of the given data.
    """
    return hashlib.sha256(data.encode()).hexdigest()
