import base64
import hashlib
import hmac
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from ..config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# AES-256 encryption setup
def get_encryption_key() -> bytes:
    """Generate or retrieve encryption key for AES-256"""
    key = os.environ.get("ENCRYPTION_KEY")
    if not key:
        # Generate a new key if not exists
        key = base64.urlsafe_b64encode(os.urandom(32))
        logger.warning("No ENCRYPTION_KEY found in environment. Generated temporary key.")
    else:
        # Ensure key is properly encoded
        key = key.encode()
    return key

# Initialize Fernet with the key
ENCRYPTION_KEY = get_encryption_key()
cipher_suite = Fernet(ENCRYPTION_KEY)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)

def encrypt_sensitive_data(data: str) -> str:
    """Encrypt sensitive data using AES-256"""
    try:
        encrypted_data = cipher_suite.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Data encryption failed"
        )

def decrypt_sensitive_data(encrypted_data: str) -> str:
    """Decrypt sensitive data using AES-256"""
    try:
        decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted_data = cipher_suite.decrypt(decoded_data)
        return decrypted_data.decode()
    except Exception as e:
        logger.error(f"Decryption failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Data decryption failed"
        )

def create_access_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def verify_token(token: str) -> Dict[str, Any]:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def generate_hmac_signature(data: str, secret: str) -> str:
    """Generate HMAC signature for data transmission verification"""
    signature = hmac.new(
        secret.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature

def verify_hmac_signature(data: str, signature: str, secret: str) -> bool:
    """Verify HMAC signature"""
    expected_signature = generate_hmac_signature(data, secret)
    return hmac.compare_digest(signature, expected_signature)

def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """Mask sensitive data for logging purposes"""
    if not data:
        return data
    
    if len(data) <= visible_chars:
        return mask_char * len(data)
    
    return data[:visible_chars] + mask_char * (len(data) - visible_chars)

def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize sensitive data before logging"""
    sensitive_fields = [
        "password", "token", "secret", "key", "credit_card", 
        "ssn", "id_number", "phone", "email"
    ]
    
    sanitized = {}
    for key, value in data.items():
        if any(field in key.lower() for field in sensitive_fields):
            if isinstance(value, str):
                sanitized[key] = mask_sensitive_data(value)
            else:
                sanitized[key] = "[REDACTED]"
        else:
            sanitized[key] = value
    
    return sanitized

def log_security_event(event_type: str, details: Dict[str, Any]) -> None:
    """Log security events with sanitized data"""
    sanitized_details = sanitize_log_data(details)
    logger.info(
        f"Security Event - {event_type}: {sanitized_details}",
        extra={"event_type": event_type, "details": sanitized_details}
    )

def generate_csrf_token() -> str:
    """Generate CSRF token"""
    return base64.urlsafe_b64encode(os.urandom(32)).decode()

def verify_csrf_token(token: str, expected_token: str) -> bool:
    """Verify CSRF token"""
    return hmac.compare_digest(token, expected_token)

def rate_limit_check(
    client_id: str, 
    max_requests: int = 100, 
    window_seconds: int = 3600
) -> bool:
    """Simple rate limiting check (in production, use Redis or similar)"""
    # This is a simplified version - in production use a proper rate limiting solution
    # For now, we'll just log the attempt
    log_security_event("rate_limit_check", {
        "client_id": client_id,
        "max_requests": max_requests,
        "window_seconds": window_seconds
    })
    return True  # Always allow for this simplified version

def validate_input_length(value: str, max_length: int) -> bool:
    """Validate input length to prevent buffer overflow"""
    return len(value) <= max_length

def sanitize_sql_input(value: str) -> str:
    """Basic SQL injection prevention"""
    # Remove dangerous SQL characters
    dangerous_chars = ["'", '"', ';', '--', '/*', '*/', 'xp_', 'sp_']
    for char in dangerous_chars:
        value = value.replace(char, '')
    return value

def generate_secure_filename(filename: str) -> str:
    """Generate secure filename for file uploads"""
    # Get file extension
    ext = os.path.splitext(filename)[1]
    # Generate random name
    secure_name = base64.urlsafe_b64encode(os.urandom(16)).decode()
    return f"{secure_name}{ext}"

# Security headers for HTTP responses
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin"
}