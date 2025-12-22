from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Member, Course, Booking

# JWT Configuration
SECRET_KEY = "your-secret-key-here"  # In production, use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class AuthService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generate password hash"""
        return pwd_context.hash(password)

    @staticmethod
    def authenticate_member(db: Session, contact: str, password: str) -> Optional[Member]:
        """Authenticate a member by contact and password"""
        member = db.query(Member).filter(Member.contact == contact).first()
        if not member:
            return None
        if not AuthService.verify_password(password, member.hashed_password):
            return None
        return member

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[str]:
        """Verify JWT token and return member contact"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            contact: str = payload.get("sub")
            if contact is None:
                return None
            return contact
        except JWTError:
            return None


class Permission:
    """Permission levels for different user roles"""
    MEMBER = "member"
    ADMIN = "admin"
    COACH = "coach"


class CoursePermission:
    """Course-specific permissions"""
    CREATE = "create_course"
    EDIT = "edit_course"
    DELETE = "delete_course"
    VIEW = "view_course"
    BOOK = "book_course"


def check_course_permission(permission: str, course_id: Optional[int] = None):
    """Check if user has specific course permission"""
    def permission_checker(
        current_member: Member = Depends(get_current_active_member),
        db: Session = Depends(get_db)
    ):
        # Admin has all permissions
        if current_member.level == "admin":
            return current_member
            
        # Coach permissions
        if current_member.level == "coach":
            if permission in [CoursePermission.VIEW, CoursePermission.EDIT]:
                if course_id:
                    course = db.query(Course).filter(Course.id == course_id).first()
                    if course and course.coach == current_member.name:
                        return current_member
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Coach can only edit their own courses"
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Coach permission required"
            )
            
        # Member permissions
        if current_member.level == "member":
            if permission == CoursePermission.VIEW:
                return current_member
            if permission == CoursePermission.BOOK:
                if course_id:
                    # Check if member already booked this course
                    existing_booking = db.query(Booking).filter(
                        Booking.member_id == current_member.id,
                        Booking.course_id == course_id
                    ).first()
                    if existing_booking:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Already booked this course"
                        )
                    return current_member
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Course ID required for booking"
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Member permission insufficient"
            )
            
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid permission level"
        )
    return permission_checker
    """Permission levels for different user roles"""
    MEMBER = "member"
    ADMIN = "admin"
    COACH = "coach"


def get_current_member(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Member:
    """Get current authenticated member"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    contact = AuthService.verify_token(token)
    if contact is None:
        raise credentials_exception
    
    member = db.query(Member).filter(Member.contact == contact).first()
    if member is None:
        raise credentials_exception
    
    return member


def get_current_active_member(
    current_member: Member = Depends(get_current_member)
) -> Member:
    """Get current active member"""
    if current_member.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive member"
        )
    return current_member


def require_permission(required_permission: str):
    """Decorator to require specific permission"""
    def permission_checker(
        current_member: Member = Depends(get_current_active_member)
    ) -> Member:
        # For simplicity, we'll use member level as permission
        # In a real app, you might have a separate permissions table
        if required_permission == Permission.ADMIN and current_member.level != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required"
            )
        if required_permission == Permission.COACH and current_member.level not in ["admin", "coach"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Coach permission required"
            )
        return current_member
    return permission_checker


def get_optional_current_member(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[Member]:
    """Get current member if token is provided, otherwise return None"""
    if token is None:
        return None
    
    try:
        contact = AuthService.verify_token(token)
        if contact is None:
            return None
        
        member = db.query(Member).filter(Member.contact == contact).first()
        if member and member.status == "active":
            return member
        return None
    except JWTError:
        return None