from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime, timedelta
import secrets
import hmac
import hashlib
from typing import Optional

from ..database import SECRET_KEY

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


def create_jwt_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def decode_jwt(token: str):
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return decoded_token if decoded_token["exp"] >= datetime.utcnow().timestamp() else None
    except JWTError:
        return None


def encrypt_data(data: str) -> str:
    """
    Encrypt sensitive data before storing in database
    """
    # In a real implementation, this would use proper encryption
    # For demo purposes, we're just returning the data as-is
    return data


def decrypt_data(encrypted_data: str) -> str:
def generate_payment_signature(payment_data: dict) -> str:
    """
    Generate HMAC signature for payment data to prevent tampering
    
    Args:
        payment_data: Dictionary containing payment details
        
    Returns:
        str: HMAC-SHA256 signature of the payment data
    """
    sorted_data = sorted(payment_data.items())
    data_string = "&".join(f"{k}={v}" for k, v in sorted_data)
    return hashlib.sha256(f"{data_string}{SECRET_KEY}".encode()).hexdigest()
    """
    Decrypt data retrieved from database
    """
    # In a real implementation, this would use proper decryption
    # For demo purposes, we're just returning the data as-is
    return encrypted_data


def check_permissions(token: str, required_permissions: list) -> bool:
    """
    Check if the user has the required permissions
    
    Args:
        token: JWT token for authentication
        required_permissions: List of required permissions (e.g. ['member:read', 'member:write'])
        
    Returns:
        bool: True if all permissions are granted, False otherwise
    """
def check_field_permissions(token: str, field_name: str, action: str) -> bool:
def check_member_permissions(token: str, member_id: int, action: str) -> bool:
    """
    Check if the user has permission to perform action on specific member
    
    Args:
        token: JWT token for authentication
        member_id: ID of the member to check
        action: 'read', 'update' or 'delete'
        
    Returns:
        bool: True if permission is granted, False otherwise
    """
    try:
        payload = decode_jwt(token)
        if not payload:
            return False
            
        # Check if user is the member themselves
        if payload.get('sub') == str(member_id):
            return True
            
        # Check staff permissions
        required_perm = f"member:{action}"
        return required_perm in payload.get("permissions", [])
    except Exception:
        return False
    """
    Check if the user has permission to access/modify specific member field
    
    Args:
        token: JWT token for authentication
        field_name: Name of the field to check (e.g. 'phone', 'email')
        action: 'read' or 'write'
        
    Returns:
        bool: True if permission is granted, False otherwise
    """
    """
    Check if the user has permission to access/modify specific field
    
    Args:
        token: JWT token for authentication
        field_name: Name of the field to check (e.g. 'phone', 'email')
        action: 'read' or 'write'
        
    Returns:
        bool: True if permission is granted, False otherwise
    """
    try:
        payload = decode_jwt(token)
        if not payload:
            return False
            
        # Get field-level permissions from token
        field_permissions = payload.get("field_permissions", {})
        
        # Check if user has required permission for the field
        required_perm = f"member:{field_name}:{action}"
        return required_perm in field_permissions.get("member", [])
    except Exception:
        return False

def validate_payment_request(payment_data: dict, token: str) -> bool:
    # Validate CSRF token
    csrf_token = payment_data.get('csrf_token')
    if not csrf_token or not verify_csrf_token(csrf_token):
        return False
    """
    Validate payment request with both signature and permissions
    
    Args:
        payment_data: Dictionary containing payment details
        token: JWT token for authentication
        
    Returns:
        bool: True if request is valid, False otherwise
    """
    signature = payment_data.pop("signature", None)
    if not signature or not verify_payment_signature(payment_data, signature):
        return False
    
    if not check_permissions(token, ["payment:process"]):
        return False
        
    return True
def verify_payment_signature(payment_data: dict, signature: str) -> bool:
    """
    Verify the HMAC signature of payment data with additional security checks

    Args:
        payment_data: Dictionary containing payment details
        signature: Signature to verify against

    Returns:
        bool: True if signature is valid, False otherwise
    """
    """
    Verify the HMAC signature of payment data with additional security checks
    
    Args:
        payment_data: Dictionary containing payment details
        signature: Signature to verify against
        
    Returns:
        bool: True if signature is valid, False otherwise
    """
    # Basic signature format validation
    if len(signature) != 64:  # SHA256 produces 64-character hex digest
        return False
    
    # Check timestamp to prevent replay attacks (within 5 minutes)
    timestamp = payment_data.get('timestamp')
    if not timestamp or abs(int(timestamp) - int(datetime.utcnow().timestamp())) > 300:
        return False
    """
    Verify the HMAC signature of payment data
    
    Args:
        payment_data: Dictionary containing payment details
        signature: Signature to verify against
        
    Returns:
        bool: True if signature is valid, False otherwise
    """
    expected_signature = generate_payment_signature(payment_data)
    return signature == expected_signature
    """
    Check if the user has the required permissions
    """
    try:
        payload = decode_jwt(token)
        if not payload:
            return False
        
        user_permissions = payload.get("permissions", [])
        return all(perm in user_permissions for perm in required_permissions)
    except Exception:
        return False

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
def generate_payment_signature(payment_data: dict) -> str:
    """
    Generate HMAC signature for payment data to prevent tampering
    
    Args:
        payment_data: Dictionary containing payment details
        
    Returns:
        str: HMAC-SHA256 signature of the payment data
    """
    # Remove sensitive fields before signing
    sanitized_data = {k: v for k, v in payment_data.items() 
                     if k not in ['cvv', 'full_card_number']}
    sorted_data = sorted(sanitized_data.items())
    data_string = "&".join(f"{k}={v}" for k, v in sorted_data)
    # Add timestamp to prevent replay attacks
    timestamp = str(int(datetime.utcnow().timestamp()))
    return hashlib.sha256(f"{data_string}&timestamp={timestamp}{SECRET_KEY}".encode()).hexdigest()

# [AUTO-APPENDED] Failed to replace, adding new code:
def validate_payment_request(payment_data: dict, token: str) -> bool:
    """
    Validate payment request with enhanced security checks
    
    Args:
        payment_data: Dictionary containing payment details
        token: JWT token for authentication
        
    Returns:
        bool: True if request is valid, False otherwise
    """
    # Validate required fields
    required_fields = ['amount', 'currency', 'description']
    if not all(field in payment_data for field in required_fields):
        return False
        
    # Validate signature
    signature = payment_data.pop("signature", None)
    if not signature or not verify_payment_signature(payment_data, signature):
        return False
        
    # Validate permissions
    if not check_permissions(token, ["payment:process"]):
        return False
        
    # Additional security checks
    try:
        amount = float(payment_data['amount'])
        if amount <= 0 or amount > 100000:  # Validate reasonable amount range
            return False
    except (ValueError, KeyError):
        return False
        
    return True

def generate_csrf_token() -> str:
    """
    Generate a CSRF token for form submissions
    
    Returns:
        str: Randomly generated CSRF token
    """
    return secrets.token_hex(32)


def verify_csrf_token(token: str) -> bool:
    """
    Verify the validity of a CSRF token
    
    Args:
        token: CSRF token to verify
        
    Returns:
        bool: True if token is valid, False otherwise
    """
    # In production, this would also check token expiration and other security checks
    return len(token) == 64  # 32 bytes in hex

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
def validate_payment_request(payment_data: dict, token: str) -> bool:
    """
    Validate payment request with enhanced security checks

    Args:
        payment_data: Dictionary containing payment details
        token: JWT token for authentication

    Returns:
        bool: True if request is valid, False otherwise
    """
    # Validate required fields
    required_fields = ['amount', 'currency', 'description', 'csrf_token']
    if not all(field in payment_data for field in required_fields):
        return False

    # Validate CSRF token
    if not verify_csrf_token(payment_data['csrf_token']):
        return False

    # Validate signature
    signature = payment_data.pop("signature", None)
    if not signature or not verify_payment_signature(payment_data, signature):
        return False

    # Validate permissions
    if not check_permissions(token, ["payment:process"]):
        return False

    # Additional security checks
    try:
        amount = float(payment_data['amount'])
        if amount <= 0 or amount > 100000:  # Validate reasonable amount range
            return False
    except (ValueError, KeyError):
        return False

    return True

# [AUTO-APPENDED] Failed to replace, adding new code:
def verify_payment_signature(payment_data: dict, signature: str) -> bool:
    """
    Verify the HMAC signature of payment data with additional security checks

    Args:
        payment_data: Dictionary containing payment details
        signature: Signature to verify

    Returns:
        bool: True if signature is valid, False otherwise
    """
    # Remove CSRF token before signature verification
    sanitized_data = {k: v for k, v in payment_data.items() if k != 'csrf_token'}
    expected_signature = generate_payment_signature(sanitized_data)
    return hmac.compare_digest(signature, expected_signature)