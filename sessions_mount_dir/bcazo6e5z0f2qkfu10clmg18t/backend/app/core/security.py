import os
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import redis

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Encryption key (should be stored securely)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
cipher_suite = Fernet(ENCRYPTION_KEY.encode())

# Redis for replay attack prevention
redis_client = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=int(os.getenv("REDIS_PORT", 6379)), db=0)

# HTTP Bearer token
security = HTTPBearer()


class SecurityManager:
    """Handles all security-related operations"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generate password hash"""
        return pwd_context.hash(password)
    
    @staticmethod
    def encrypt_data(data: str) -> str:
        """Encrypt sensitive data"""
        return cipher_suite.encrypt(data.encode()).decode()
    
    @staticmethod
    def decrypt_data(encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return cipher_suite.decrypt(encrypted_data.encode()).decode()
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    def generate_request_signature(request_data: Dict[str, Any], timestamp: str) -> str:
        """Generate HMAC signature for request"""
        # Sort keys for consistent signature
        sorted_data = sorted(request_data.items())
        message = str(sorted_data) + timestamp
        signature = hmac.new(
            SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    @staticmethod
    def verify_request_signature(request_data: Dict[str, Any], timestamp: str, signature: str) -> bool:
        """Verify HMAC signature"""
        expected_signature = SecurityManager.generate_request_signature(request_data, timestamp)
        return hmac.compare_digest(signature, expected_signature)
    
    @staticmethod
    def check_replay_attack(request_id: str, window_seconds: int = 300) -> bool:
        """Check for replay attacks using Redis"""
        if redis_client.exists(f"replay:{request_id}"):
            return False
        redis_client.setex(f"replay:{request_id}", window_seconds, "1")
        return True
    
    @staticmethod
    def validate_timestamp(timestamp: str, window_seconds: int = 300) -> bool:
        """Validate request timestamp to prevent replay attacks"""
        try:
            request_time = datetime.fromisoformat(timestamp)
            current_time = datetime.utcnow()
            time_diff = abs((current_time - request_time).total_seconds())
            return time_diff <= window_seconds
        except ValueError:
            return False


class HTTPSRedirectMiddleware:
    """Middleware to enforce HTTPS"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("scheme") != "https":
            # In production, this should redirect to HTTPS
            # For development, we'll just log a warning
            print("WARNING: HTTP request detected. HTTPS should be enforced in production.")
        await self.app(scope, receive, send)


class SecurityHeadersMiddleware:
    """Middleware to add security headers"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Add security headers
            headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "Content-Security-Policy": "default-src 'self'",
            }
            
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    message["headers"].extend(
                        [(k.encode(), v.encode()) for k, v in headers.items()]
                    )
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)


def get_current_user(credentials: HTTPAuthorizationCredentials = security) -> Dict[str, Any]:
    """Get current user from JWT token"""
    token = credentials.credentials
    payload = SecurityManager.verify_token(token)
    return payload


def require_https(request: Request):
    """Check if request is HTTPS"""
    if request.url.scheme != "https" and not os.getenv("DEBUG", "false").lower() == "true":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="HTTPS required"
        )


def validate_payment_request(request_data: Dict[str, Any], headers: Dict[str, str]) -> bool:
    """Validate payment request with signature and replay protection"""
    # Get required headers
    timestamp = headers.get("X-Timestamp")
    signature = headers.get("X-Signature")
    request_id = headers.get("X-Request-ID")
    
    if not all([timestamp, signature, request_id]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing security headers"
        )
    
    # Validate timestamp
    if not SecurityManager.validate_timestamp(timestamp):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired timestamp"
        )
    
    # Check for replay attack
    if not SecurityManager.check_replay_attack(request_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate request detected"
        )
    
    # Verify signature
    if not SecurityManager.verify_request_signature(request_data, timestamp, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid request signature"
        )
    
    return True


def encrypt_payment_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Encrypt sensitive payment data"""
    encrypted_data = {}
    sensitive_fields = ["card_number", "cvv", "expiry"]
    
    for key, value in data.items():
        if key in sensitive_fields:
            encrypted_data[key] = SecurityManager.encrypt_data(str(value))
        else:
            encrypted_data[key] = value
    
    return encrypted_data


def decrypt_payment_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Decrypt sensitive payment data"""
    decrypted_data = {}
    sensitive_fields = ["card_number", "cvv", "expiry"]
    
    for key, value in data.items():
        if key in sensitive_fields:
            decrypted_data[key] = SecurityManager.decrypt_data(value)
        else:
            decrypted_data[key] = value
    
    return decrypted_data
