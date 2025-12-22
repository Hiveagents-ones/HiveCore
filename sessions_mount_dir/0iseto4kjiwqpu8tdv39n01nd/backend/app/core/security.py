import os
from datetime import datetime, timedelta
from typing import Any, Union, Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from fastapi import HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from .config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

# AES encryption key (should be stored securely)
AES_KEY = os.environ.get("AES_KEY", Fernet.generate_key()).encode()
cipher_suite = Fernet(AES_KEY)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)

def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token."""
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
    """Verify JWT token and return subject."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        subject: str = payload.get("sub")
        if subject is None:
            return None
        return subject
    except JWTError:
        return None

def encrypt_data(data: str) -> str:
    """Encrypt data using AES."""
    encrypted_data = cipher_suite.encrypt(data.encode())
    return encrypted_data.decode()

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt data using AES."""
    decrypted_data = cipher_suite.decrypt(encrypted_data.encode())
    return decrypted_data.decode()

def check_permissions(user_permissions: list[str], required_permissions: list[str]) -> bool:
    """Check if user has required permissions."""
    return all(perm in user_permissions for perm in required_permissions)

def enforce_https(request: Request):
    """Enforce HTTPS redirect if request is not secure."""
    if not request.url.is_secure and not settings.DEBUG:
        https_url = request.url.replace(scheme="https")
        raise HTTPException(
            status_code=status.HTTP_301_MOVED_PERMANENTLY,
            detail="Use HTTPS",
            headers={"Location": str(https_url)}
        )

def get_current_user_id(token: str = oauth2_scheme) -> str:
    """Get current user ID from token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = verify_token(token)
    if user_id is None:
        raise credentials_exception
    return user_id

def require_permissions(required_permissions: list[str]):
    """Decorator to require specific permissions."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # This is a simplified version - in production you'd get user permissions from DB
            user_permissions = kwargs.get("user_permissions", [])
            if not check_permissions(user_permissions, required_permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator
