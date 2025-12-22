from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta
from typing import Optional
from .database import get_db

# Security configuration
SECRET_KEY = "your-secret-key"  # Should be in environment variables in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(status_code=403, detail="Invalid token or expired token.")
            return credentials.credentials
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")

    def verify_jwt(self, jwtoken: str) -> bool:
        isTokenValid: bool = False
        try:
            payload = decode_jwt(jwtoken)
        except:
            payload = None
        if payload:
            isTokenValid = True
        return isTokenValid

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_jwt(token: str):
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded_token if decoded_token["exp"] >= datetime.utcnow().timestamp() else None
    except:
        return None

def encrypt_data(data: str) -> str:
    # Placeholder for data encryption logic
    # In production, use proper encryption like AES
    return data

def decrypt_data(encrypted_data: str) -> str:
    # Placeholder for data decryption logic
    return encrypted_data

def check_permissions(token: str, required_permissions: list) -> bool:
    """
    Check if the user has the required permissions
    :param token: JWT token
    :param required_permissions: List of required permissions
    :return: Boolean indicating if user has permissions
    """
    try:
        payload = decode_jwt(token)
        if not payload:
            return False
        user_permissions = payload.get("permissions", [])
        return all(perm in user_permissions for perm in required_permissions)
    except:
        return False

def get_current_user(token: str):
    """
    Get current user from JWT token
    :param token: JWT token
    :return: User ID if valid, None otherwise
    """
    try:
        payload = decode_jwt(token)
        if payload:
            return payload.get("sub")
        return None
    except:
        return None