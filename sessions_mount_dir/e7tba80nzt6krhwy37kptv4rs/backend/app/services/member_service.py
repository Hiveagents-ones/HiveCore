import re
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from app.models.member import Member
from app.schemas.member import MemberCreate
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def validate_phone(phone: str) -> bool:
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, phone))

def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))

def generate_member_id() -> str:
    return str(uuid.uuid4()).replace('-', '')[:8]

def create_member(db: Session, member_data: MemberCreate) -> Member:
    # Validate phone and email format
    if not validate_phone(member_data.phone):
        raise ValueError("Invalid phone number format")
    if not validate_email(member_data.email):
        raise ValueError("Invalid email format")
    
    # Check for existing registration
    if db.query(Member).filter(Member.phone == member_data.phone).first():
        raise ValueError("Phone number already registered")
    if db.query(Member).filter(Member.email == member_data.email).first():
        raise ValueError("Email already registered")
    
    # Generate secure member ID
    member_id = generate_member_id()
    
    # Hash password securely
    hashed_password = pwd_context.hash(member_data.password)
    
    # Create member record
    db_member = Member(
        member_id=member_id,
        phone=member_data.phone,
        email=member_data.email,
        hashed_password=hashed_password,
        name=member_data.name,
        status="active"
    )
    
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member