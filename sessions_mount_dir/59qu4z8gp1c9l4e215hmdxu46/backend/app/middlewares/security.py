from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
from cryptography.fernet import Fernet
from jwt import PyJWTError
from fastapi import Depends

from ..database import SessionLocal
from ..models import Member, MemberCard
from ..models import CourseBooking
from ..models import RevokedToken

from ..models import CoachSchedule

# Security configurations
from ..config import settings

SECRET_KEY = settings.SECRET_KEY
ENCRYPTION_KEY = settings.ENCRYPTION_KEY.encode()
FERNET = Fernet(ENCRYPTION_KEY)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
ROLES = {
    "COURSE_MANAGER": "course_manager",
    "MEMBER": "member",
    "COACH": "coach",
    "ADMIN": "admin"
}

class JWTBearer(HTTPBearer):
    """
    JWT Bearer token authentication middleware
    """
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[Dict[str, Any]]:
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authorization code."
            )
        
        if not credentials.scheme == "Bearer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authentication scheme."
            )
        
        payload = self.verify_jwt(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid token or expired token."
            )
        
        return payload

    def verify_jwt(self, jwtoken: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token with enhanced security checks:
        - Token revocation check
        - Token structure validation
        - Expiration check
        - Required claims validation
        """
        # Check token revocation first
        db = SessionLocal()
        try:
            revoked_token = db.query(RevokedToken).filter(RevokedToken.token == jwtoken).first()
            if revoked_token:
                return None
        finally:
            db.close()
        """
        Verify JWT token with additional security checks
        - Validate token structure
        - Check token expiration
        - Validate required claims
        """
        try:
            # Additional security: verify audience and issuer if needed
            payload = jwt.decode(
                jwtoken,
                SECRET_KEY,
                algorithms=[ALGORITHM],
                options={
                    "require": ["exp", "sub", "role"],
                    "verify_aud": False,
                    "verify_iss": False
                }
            )
            
            # Validate required claims
            if not all(key in payload for key in ["sub", "role"]):
                return None
                
            return payload
        except PyJWTError as e:
            # Log the error for security monitoring
            print(f"JWT verification failed: {str(e)}")
            return None

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def encrypt_sensitive_data(data: str, include_timestamp: bool = True) -> str:
    """
    Encrypt sensitive data using Fernet symmetric encryption with additional security measures
    Args:
        data: String data to encrypt
    Returns:
        Encrypted string (URL-safe base64)
    Raises:
        HTTPException: If encryption fails
    """
    if not data:
        return ""
    try:
        # Add timestamp to detect replay attacks
        timestamp = datetime.utcnow().isoformat()
        data_with_timestamp = f"{timestamp}:{data}"
        encrypted = FERNET.encrypt(data_with_timestamp.encode())
        return encrypted.decode()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data encryption failed: {str(e)}"
        )
    Returns:
        Encrypted string
    Raises:
        HTTPException: If encryption fails
    """
    try:
        if not data:
            raise ValueError("Empty data cannot be encrypted")
        
        # Add timestamp and random padding for additional security
        padded_data = f"{datetime.utcnow().isoformat()}|{data}|{SECRET_KEY[-8:]}"
        return FERNET.encrypt(padded_data.encode()).decode()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data encryption failed: {str(e)}"
        )


def decrypt_sensitive_data(encrypted_data: str, check_timestamp: bool = True) -> str:
    """
    Decrypt sensitive data using Fernet symmetric encryption with validation
    Args:
        encrypted_data: Encrypted string to decrypt
    Returns:
        Original decrypted string
    Raises:
        HTTPException: If decryption fails or data is tampered
    """
    if not encrypted_data:
        return ""
    try:
        decrypted = FERNET.decrypt(encrypted_data.encode()).decode()
        # Split timestamp and actual data
        timestamp_str, data = decrypted.split(":", 1)
        timestamp = datetime.fromisoformat(timestamp_str)
        
        # Validate timestamp is not too old (e.g., 1 hour)
        if datetime.utcnow() - timestamp > timedelta(hours=1):
            raise ValueError("Decrypted data timestamp expired")
            
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data decryption failed: {str(e)}"
        )        encrypted_data: Encrypted string to decrypt
    Returns:
        Original decrypted string without padding
    Raises:
        HTTPException: If decryption fails or data is tampered
    """
    try:
        if not encrypted_data:
            raise ValueError("Empty encrypted data")
            
        decrypted = FERNET.decrypt(encrypted_data.encode()).decode()
        parts = decrypted.split("|")
        
        # Validate the decrypted data structure
        if len(parts) != 3:
            raise ValueError("Invalid encrypted data format")
            
        # Verify the secret key fragment
        if parts[2] != SECRET_KEY[-8:]:
            raise ValueError("Data tampering detected")
            
        # Optionally validate timestamp if needed
        # datetime.fromisoformat(parts[0])
        
        return parts[1]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data decryption failed: {str(e)}"
        )
    """
    Create JWT access token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_member(token: str = Depends(JWTBearer()), decrypt_fields: bool = True) -> Member:
    """
    Get current authenticated member from JWT token with enhanced security
    Args:
        token: JWT token payload
        decrypt_fields: Whether to decrypt sensitive fields automatically
    Returns:
        Member object
    Raises:
        HTTPException: If member not found or decryption fails
    """
    # First verify the token has member role
    check_role(token, ROLES["MEMBER"])
    """
    Get current authenticated member from JWT token with enhanced security
    Args:
        token: JWT token payload
        decrypt_fields: Whether to decrypt sensitive fields automatically
    Returns:
        Member object
    Raises:
        HTTPException: If member not found or decryption fails
    """
    """
    Get current authenticated member from JWT token
    Args:
        token: JWT token payload
        decrypt_fields: Whether to decrypt encrypted fields automatically
    Returns:
        Member object
    """
    db = SessionLocal()
    try:
        member = db.query(Member).filter(Member.id == token.get("sub")).first()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )
            
        # Automatically decrypt sensitive fields if enabled
        if decrypt_fields:
            for field in ["phone", "email", "emergency_contact"]:
                if getattr(member, field, None):
                    try:
                        setattr(member, field, decrypt_sensitive_data(getattr(member, field)))
                    except Exception as e:
                        # Log but don't fail the request for decryption errors
                        print(f"Failed to decrypt {field}: {str(e)}")
                        
        return member
    finally:
        db.close()


def check_membership_active(token: str = Depends(JWTBearer())) -> bool:
    """
    Check if member has active membership
    Args:
        token: JWT token payload
    Returns:
        bool: True if membership is active
    """
    db = SessionLocal()
    try:
        member_card = db.query(MemberCard).filter(
            MemberCard.member_id == token.get("sub"),
            MemberCard.status == "active"
        ).first()
        
        if not member_card:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Membership is not active"
            )
        return True
    finally:
        db.close()
def check_role(token: str = Depends(JWTBearer()), required_role: str = None) -> bool:
    """
    Enhanced role checking with hierarchy validation
    Args:
        token: JWT token payload
        required_role: Required role for the operation
    Returns:
        bool: True if role matches or is higher in hierarchy
    Raises:
        HTTPException: If role check fails
    """
    """
    Check if user has the required role with enhanced validation
    Args:
        token: JWT token payload
        required_role: Required role (defaults to member)
    Returns:
        bool: True if role check passes
    Raises:
        HTTPException: If role check fails
    """
    if not required_role:
        required_role = ROLES["MEMBER"]
    
    if required_role not in ROLES.values():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role specified"
        )
    
    if token.get("role") != required_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return TrueMBER"], allow_higher: bool = False) -> bool:
def check_course_permission(token: str = Depends(JWTBearer()), course_id: int = None, booking_operation: bool = False, schedule_id: int = None) -> bool:
def check_coach_permission(token: str = Depends(JWTBearer()), coach_id: int = None) -> bool:

def check_coach_schedule_permission(token: str = Depends(JWTBearer()), schedule_id: int = None, require_write: bool = False) -> bool:
    """
    Check if user has permission to access coach schedule operations with enhanced validation
    Args:
        token: JWT token payload
        schedule_id: Optional schedule ID for ownership validation
        require_write: Whether the operation requires write permissions
    Returns:
        bool: True if permission granted
    """
    db = SessionLocal()
    try:
        # Admins have full access
        if token.get("role") == ROLES["ADMIN"]:
            return True

        # Coaches can only access/modify their own schedules
        if token.get("role") == ROLES["COACH"]:
            if schedule_id:
                schedule = db.query(CoachSchedule).filter(
                    CoachSchedule.id == schedule_id,
                    CoachSchedule.coach_id == token.get("sub")
                ).first()
                if not schedule:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Can only access own schedules"
                    )
            return True

        # Course managers can view all schedules but only modify with additional validation
        if token.get("role") == ROLES["COURSE_MANAGER"]:
            if require_write and schedule_id:
                # Additional validation for modification operations
                schedule = db.query(CoachSchedule).filter(
                    CoachSchedule.id == schedule_id
                ).first()
                if not schedule:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Schedule not found"
                    )
                # Check if schedule is in the future
                if schedule.start_time < datetime.utcnow():
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot modify past schedules"
                    )
            return True

        # Members can only view schedules (read-only)
        if token.get("role") == ROLES["MEMBER"]:
            if require_write:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Members cannot modify schedules"
                )
            return True

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for schedule operation"
        )
    finally:
        db.close()
def check_booking_permission(token: str = Depends(JWTBearer()), booking_id: int = None, schedule_id: int = None) -> bool:
    """
    Check if user has permission to access booking
    Args:
        token: JWT token payload
        booking_id: Booking ID to validate ownership
    Returns:
        bool: True if permission granted
    """
    db = SessionLocal()
    try:
        # Admins and course managers have full access
        if token.get("role") in [ROLES["ADMIN"], ROLES["COURSE_MANAGER"]]:
            return True

        # Members can only access their own bookings
        if token.get("role") == ROLES["MEMBER"]:
            if booking_id or schedule_id:
                query = db.query(CourseBooking)
                if booking_id:
                    query = query.filter(CourseBooking.id == booking_id)
                if schedule_id:
                    query = query.filter(CourseBooking.schedule_id == schedule_id)
                booking = query.filter(
                    CourseBooking.member_id == token.get("sub")
                ).first()
                if not booking:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Can only access own bookings"
                    )
            return True

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for booking operation"
        )
    finally:
        db.close()

def check_coach_schedule_permission(token: str = Depends(JWTBearer()), schedule_id: int = None) -> bool:
    """
    Check if user has permission to access coach schedule operations
    Args:
        token: JWT token payload
        schedule_id: Optional schedule ID for ownership validation
    Returns:
        bool: True if permission granted
    """
    db = SessionLocal()
    try:
        # Admins have full access
        if token.get("role") == ROLES["ADMIN"]:
            return True

        # Coaches can only access their own schedules
        if token.get("role") == ROLES["COACH"]:
            if schedule_id:
                schedule = db.query(CoachSchedule).filter(
                    CoachSchedule.id == schedule_id,
                    CoachSchedule.coach_id == token.get("sub")
                ).first()
                if not schedule:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Can only access own schedules"
                    )
            return True

        # Course managers can view all schedules
        if token.get("role") == ROLES["COURSE_MANAGER"]:
            return True

        # Members can view schedules but not modify
        if token.get("role") == ROLES["MEMBER"]:
            return True

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for schedule operation"
        )
    finally:
        db.close()
    """
    Check if user has permission to access coach-related operations
    Args:
        token: JWT token payload
        coach_id: Optional coach ID for ownership validation
    Returns:
        bool: True if permission granted
    """
    # Admins have full access
    if token.get("role") == ROLES["ADMIN"]:
        return True

    # Coaches can only access their own data
    if token.get("role") == ROLES["COACH"]:
        if coach_id and str(token.get("sub")) != str(coach_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only access own coach data"
            )
        return True

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions for coach operation"
    )
    """
    Check if user has permission to access course-related operations
    Args:
        token: JWT token payload
        course_id: Optional course ID for ownership validation
    Returns:
        bool: True if permission granted
    """
    # Admins and course managers have full access
    if token.get("role") in [ROLES["ADMIN"], ROLES["COURSE_MANAGER"]]:
        return True
        
    # Members can only access their own bookings
    if token.get("role") == ROLES["MEMBER"]:
        if booking_operation:
            if schedule_id:
                db = SessionLocal()
                try:
                    booking = db.query(CourseBooking).filter(
                        CourseBooking.member_id == token.get("sub"),
                        CourseBooking.schedule_id == schedule_id
                    ).first()
                    if not booking:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Can only access own bookings"
                        )
                finally:
                    db.close()
            return True
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Members can only perform booking operations"
        )
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions for course operation"
    )
    """
    Check if user has required role
    Args:
        token: JWT token payload
        required_role: Required role for the operation
    Returns:
        bool: True if role matches
    """
    user_role = token.get("role")
    if user_role != required_role:
        if allow_higher:
            # Check if user has higher privilege than required
            role_hierarchy = [ROLES["MEMBER"], ROLES["COACH"], ROLES["COURSE_MANAGER"], ROLES["ADMIN"]]
            if role_hierarchy.index(user_role) > role_hierarchy.index(required_role):
                return True
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Required role: {required_role}"
        )
    return True


def get_current_member_with_role(token: str = Depends(JWTBearer())) -> Member:
    """
    Get current authenticated member with role validation
    """
    check_role(token, ROLES["MEMBER"])
    return get_current_member(token)
def get_current_member_for_booking(token: str = Depends(JWTBearer())) -> Member:
    """
    Get current authenticated member with booking permission validation
    """
    check_course_permission(token, booking_operation=True)
    return get_current_member(token)
    """
    Get current authenticated member with booking permission validation
    """
    check_course_permission(token, booking_operation=True)
    return get_current_member(token)
    """
    Get current authenticated member with role validation
    """
    check_role(token, ROLES["MEMBER"])
    return get_current_member(token)


def get_current_member_for_course(token: str = Depends(JWTBearer())) -> Member:
def get_current_member_for_booking(token: str = Depends(JWTBearer())) -> Member:
    """
    Get current authenticated member with booking permission validation
    """
    check_course_permission(token, booking_operation=True)
    return get_current_member(token)
    """
    Get current authenticated member with course permission validation
    """
    check_course_permission(token)
    return get_current_member(token)


def get_current_coach(token: str = Depends(JWTBearer())) -> Coach:

def get_current_coach_for_schedule(token: str = Depends(JWTBearer()), require_schedule_access: bool = True) -> Coach:
    """
    Get current authenticated coach with enhanced schedule permission validation
    Args:
        token: JWT token payload
        require_schedule_access: Whether to validate schedule access permissions
    Returns:
        Coach: Authenticated coach object
    """
    check_role(token, ROLES["COACH"])
    
    db = SessionLocal()
    try:
        coach = db.query(Coach).filter(Coach.id == token.get("sub")).first()
        if not coach:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Coach not found"
            )
            
        if require_schedule_access and not coach.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Coach account is not active for scheduling"
            )
            
        return coach
    finally:
        db.close()

def get_current_coach_for_schedule(token: str = Depends(JWTBearer())) -> Coach:
    """
    Get current authenticated coach with schedule permission validation
    """
    check_role(token, ROLES["COACH"])
    return get_current_coach(token)

def check_booking_permission(token: str = Depends(JWTBearer()), booking_id: int = None) -> bool:
    """
    Check if user has permission to access booking
    Args:
        token: JWT token payload
        booking_id: Booking ID to validate ownership
    Returns:
        bool: True if permission granted
    """
    db = SessionLocal()
    try:
        # Admins and course managers have full access
        if token.get("role") in [ROLES["ADMIN"], ROLES["COURSE_MANAGER"]]:
            return True

        # Members can only access their own bookings
        if token.get("role") == ROLES["MEMBER"]:
            if booking_id:
                booking = db.query(CourseBooking).filter(
                    CourseBooking.id == booking_id,
                    CourseBooking.member_id == token.get("sub")
                ).first()
                if not booking:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Can only access own bookings"
                    )
            return True

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for booking operation"
        )
    finally:
        db.close()
    """
    Get current authenticated coach from JWT token
    Args:
        token: JWT token payload
    Returns:
        Coach object
    """
    db = SessionLocal()
    try:
        check_role(token, ROLES["COACH"])
        coach = db.query(Coach).filter(Coach.id == token.get("sub")).first()
        if not coach:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Coach not found"
            )
        return coach
    finally:
        db.close()

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
def check_course_permission(token: str = Depends(JWTBearer()), course_id: int = None, booking_operation: bool = False, schedule_id: int = None) -> bool:
    """
    Check if user has permission to access course-related operations
    Args:
        token: JWT token payload
        course_id: Optional course ID for ownership validation
    Returns:
        bool: True if permission granted
    """
    # Admins and course managers have full access
    if token.get("role") in [ROLES["ADMIN"], ROLES["COURSE_MANAGER"]]:
        return True

    # Members can only access their own bookings
    if token.get("role") == ROLES["MEMBER"]:
        if booking_operation:
            return True
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Members can only perform booking operations"
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions for course operation"
    )


def check_coach_permission(token: str = Depends(JWTBearer()), coach_id: int = None) -> bool:
    """
    Check if user has permission to access coach-related operations
    Args:
        token: JWT token payload
        coach_id: Optional coach ID for ownership validation
    Returns:
        bool: True if permission granted
    """
    # Admins have full access
    if token.get("role") == ROLES["ADMIN"]:
        return True

    # Coaches can only access their own data
    if token.get("role") == ROLES["COACH"]:
        if coach_id and str(token.get("sub")) != str(coach_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only access own coach data"
            )
        return True

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions for coach operation"
    )

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
def encrypt_sensitive_data(data: str) -> str:
    """
    Encrypt sensitive data using Fernet symmetric encryption with additional security measures
    Args:
        data: String data to encrypt
    Returns:
        Encrypted string
    Raises:
        HTTPException: If encryption fails
    """
    try:
        if not data:
            raise ValueError("Empty data cannot be encrypted")

        # Add timestamp if requested
        padded_data = f"{datetime.utcnow().isoformat()}:{data}" if include_timestamp else data
        encrypted_data = FERNET.encrypt(padded_data.encode())
        return encrypted_data.decode()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data encryption failed: {str(e)}"
        )

# [AUTO-APPENDED] Failed to replace, adding new code:
def decrypt_sensitive_data(encrypted_data: str) -> str:
    """
    Decrypt sensitive data using Fernet symmetric encryption with validation
    Args:
        encrypted_data: String data to decrypt
    Returns:
        Decrypted string
    Raises:
        HTTPException: If decryption fails or data is invalid
    """
    try:
        if not encrypted_data:
            raise ValueError("Empty encrypted data")
            
        decrypted_data = FERNET.decrypt(encrypted_data.encode()).decode()
        # Split timestamp if present
        if ":" in decrypted_data and check_timestamp:
            timestamp, data = decrypted_data.split(":", 1)
            # Validate timestamp is within reasonable range
            data_time = datetime.fromisoformat(timestamp)
            if datetime.utcnow() - data_time > timedelta(days=1):
                raise ValueError("Decrypted data is too old")
        else:
            data = decrypted_data
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data decryption failed: {str(e)}"
        )

# [AUTO-APPENDED] Failed to replace, adding new code:
def get_current_member(token: str = Depends(JWTBearer()), decrypt_fields: bool = True) -> Member:
    """
    Get current authenticated member from JWT token with enhanced security
    Args:
        token: JWT token payload
        decrypt_fields: Whether to decrypt sensitive fields automatically
    Returns:
        Member object
    Raises:
        HTTPException: If member not found or decryption fails
    """
    # First verify the token has member role
    check_role(token, ROLES["MEMBER"])
    
    db = SessionLocal()
    try:
        member = db.query(Member).filter(Member.id == token.get("sub")).first()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )

        if decrypt_fields:
            try:
                if member.email:
                    member.email = decrypt_sensitive_data(member.email)
                if member.phone:
                    member.phone = decrypt_sensitive_data(member.phone)
            except HTTPException:
                # Don't fail entire request if decryption fails
                pass

        return member
    finally:
        db.close()

# [AUTO-APPENDED] Failed to insert:
    check_role(token, ROLES["MEMBER"])
    db = SessionLocal()
    try:
        member = db.query(Member).filter(Member.id == token.get("sub")).first()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )
            
        if decrypt_fields:
            try:
                if member.email:
                    member.email = decrypt_sensitive_data(member.email)
                if member.phone:
                    member.phone = decrypt_sensitive_data(member.phone)
            except HTTPException:
                # Don't fail entire request if decryption fails
                pass
                
        return member
    finally:
        db.close()

def filter_member_data(member: Member, include_sensitive: bool = False) -> dict:
    """
    Filter member data based on permissions and sensitivity
    Args:
        member: Member object to filter
        include_sensitive: Whether to include sensitive fields
    Returns:
        dict: Filtered member data
    """
    base_fields = {
        'id', 'name', 'join_date', 'membership_status', 
        'points', 'level', 'avatar_url'
    }
    sensitive_fields = {
        'phone', 'email', 'emergency_contact', 
        'address', 'id_number', 'birth_date'
    }
    
    member_dict = {k: v for k, v in member.__dict__.items() 
                  if not k.startswith('_')}
    
    if include_sensitive:
        return {k: v for k, v in member_dict.items() 
               if k in base_fields.union(sensitive_fields)}
    else:
        return {k: v for k, v in member_dict.items() 
               if k in base_fields}

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
def filter_member_data(member: Member, include_sensitive: bool = False) -> dict:
    """
    Filter member data based on permissions and sensitivity with enhanced security
    Args:
        member: Member object to filter
        include_sensitive: Whether to include sensitive fields (requires proper permissions)
    Returns:
        dict: Filtered member data with proper redaction and formatting
    Raises:
        ValueError: If member object is invalid
    """
    if not member or not isinstance(member, Member):
        raise ValueError("Invalid member object provided")

    # Base fields always visible
    base_fields = {
        'id', 'name', 'join_date', 'membership_status',
        'points', 'level', 'avatar_url', 'gender'
    }
    
    # Sensitive fields requiring explicit permission
    sensitive_fields = {
        'phone', 'email', 'emergency_contact',
        'address', 'id_number', 'birth_date', 'medical_notes'
    }

    # Create filtered dict excluding SQLAlchemy internals
    member_dict = {
        k: v for k, v in member.__dict__.items()
        if not k.startswith('_')
    }

    # Apply filtering based on sensitivity
    filtered_data = {}
    for field, value in member_dict.items():
        if field in base_fields:
            filtered_data[field] = value
        elif include_sensitive and field in sensitive_fields:
            # Apply additional formatting for sensitive fields
            if field == 'phone' and value:
                filtered_data[field] = f"{value[:3]}****{value[-2:]}"
            elif field == 'id_number' and value:
                filtered_data[field] = f"{value[:1]}************{value[-1:]}"
            else:
                filtered_data[field] = value

    return filtered_data
def filter_member_data(member: Member, include_sensitive: bool = False) -> dict:
    """
    Filter member data based on permissions and sensitivity with enhanced security
    Args:
        member: Member object to filter
        include_sensitive: Whether to include sensitive fields (requires proper permissions)
    Returns:
        dict: Filtered member data with proper redaction and formatting
    Raises:
        ValueError: If member object is invalid
    """
    if not member or not isinstance(member, Member):
        raise ValueError("Invalid member object provided")

    # Base fields always visible
    base_fields = {
        'id', 'name', 'join_date', 'membership_status',
        'points', 'level', 'avatar_url', 'gender'
    }

    # Sensitive fields requiring explicit permission
    sensitive_fields = {
        'phone', 'email', 'emergency_contact',
        'address', 'id_number', 'birth_date', 'medical_notes'
    }

    # Create filtered dict excluding SQLAlchemy internals
    member_dict = {
        k: v for k, v in member.__dict__.items()
        if not k.startswith('_')
    }

    # Apply filtering based on sensitivity
    filtered_data = {}
    for field, value in member_dict.items():
        if field in base_fields:
            filtered_data[field] = value
        elif include_sensitive and field in sensitive_fields:
            # Apply additional formatting for sensitive fields
            if field == 'phone' and value:
                filtered_data[field] = f"{value[:3]}****{value[-2:]}"
            elif field == 'id_number' and value:
                filtered_data[field] = f"{value[:1]}************{value[-1:]}"
            else:
                filtered_data[field] = value

    return filtered_data

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
def decrypt_sensitive_data(encrypted_data: str) -> str:
    """
    Decrypt sensitive data using Fernet symmetric encryption with validation
    Args:
        encrypted_data: Encrypted string to decrypt
    Returns:
        str: Decrypted string
    Raises:
        ValueError: If decryption fails or data is invalid
    """
    if not encrypted_data:
        return ""
    try:
        decrypted_data = FERNET.decrypt(encrypted_data.encode()).decode()
        if not decrypted_data or not isinstance(decrypted_data, str):
            raise ValueError("Invalid decrypted data")
        return decrypted_data
    except Exception as e:
        # Log the error but return generic message for security
        print(f"Decryption failed: {str(e)}")
        raise ValueError("Failed to decrypt sensitive data")

# [AUTO-APPENDED] Failed to replace, adding new code:
def get_current_member(token: str = Depends(JWTBearer()), decrypt_fields: bool = True) -> Member:
    """
    Get current authenticated member from JWT token with enhanced security
    Args:
        token: JWT token from request header
        decrypt_fields: Whether to decrypt sensitive fields
    Returns:
        Member: Authenticated member object
    Raises:
        HTTPException: If authentication fails or member not found
    """
    db = SessionLocal()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        member_id = payload.get("sub")
        if not member_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )

        member = db.query(Member).filter(Member.id == member_id).first()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )

        if decrypt_fields:
            # Decrypt sensitive fields
            try:
                if member.phone:
                    member.phone = decrypt_sensitive_data(member.phone)
                if member.email:
                    member.email = decrypt_sensitive_data(member.email)
                if member.id_number:
                    member.id_number = decrypt_sensitive_data(member.id_number)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to decrypt member data"
                )

        return member
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    finally:
        db.close()