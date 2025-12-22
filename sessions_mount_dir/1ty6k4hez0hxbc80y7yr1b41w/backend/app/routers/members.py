from fastapi import Security, status
from fastapi.security import APIKeyHeader
from cryptography.fernet import Fernet
import os

API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Initialize encryption
key = os.getenv("ENCRYPTION_KEY", "default_key_that_should_be_changed_in_production")
cipher_suite = Fernet(key.encode())

def get_current_user(api_key: str = Security(api_key_header)):
    """
    Validate API key from header
    """
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )
    return True

def encrypt_data(data: str) -> str:
    """Encrypt sensitive data"""
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data"""
    return cipher_suite.decrypt(encrypted_data.encode()).decode()
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from ..database import get_db, Member

router = APIRouter(
    prefix="/api/v1/members",
    tags=["members"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[dict])
def read_members(
    skip: int = 0, 
    limit: int = 100, 
    name: str = None, 
    db: Session = Depends(get_db),
    auth: bool = Depends(get_current_user)
):
    """
    Get list of members with pagination and optional filtering
    - skip: number of records to skip
    - limit: maximum number of records to return
    - name: optional name filter (partial match)
    """
    query = db.query(Member).order_by(Member.id)
    
    if name:
        query = query.filter(Member.name.ilike(f"%{name}%"))
        
    members = query.offset(skip).limit(limit).all()
    return [{
        "id": member.id,
        "name": member.name,
        "phone": member.phone,
        "email": member.email,
        "join_date": member.join_date
    } for member in members]

@router.get("/{member_id}", response_model=dict)
def read_member(
    member_id: int,
    db: Session = Depends(get_db),
    auth: bool = Depends(get_current_user)
):
    """
    Get member by ID
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return {
        "id": member.id,
        "name": member.name,
        "phone": decrypt_data(member.phone) if member.phone else None,
        "email": decrypt_data(member.email) if member.email else None,
        "join_date": member.join_date
    }

@router.post("/", response_model=dict)
def create_member(
    name: str,
    phone: str,
    email: str,
    join_date: date,
    db: Session = Depends(get_db),
    auth: bool = Depends(get_current_user)
):
    """
    Create new member
    """
    # Check if phone or email already exists
    existing_member = db.query(Member).filter(
        (Member.phone == phone) | (Member.email == email)
    ).first()
    if existing_member:
        raise HTTPException(
            status_code=400,
            detail="Phone or email already registered"
        )
    
    db_member = Member(
        name=name,
        phone=encrypt_data(phone),
        email=encrypt_data(email),
        join_date=join_date
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return {
        "id": db_member.id,
        "name": db_member.name,
        "phone": db_member.phone,
        "email": db_member.email,
        "join_date": db_member.join_date
    }

@router.put("/{member_id}", response_model=dict)
def update_member(
    member_id: int,
    name: str = None,
    phone: str = None,
    email: str = None,
    db: Session = Depends(get_db)
):
    """
    Update member information
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    
    if name:
        member.name = name
    if phone:
        # Check if new phone already exists
        encrypted_phone = encrypt_data(phone)
        if encrypted_phone != member.phone and db.query(Member).filter(Member.phone == encrypted_phone).first():
            raise HTTPException(status_code=400, detail="Phone already registered")
        member.phone = encrypted_phone
    if email:
        # Check if new email already exists
        encrypted_email = encrypt_data(email)
        if encrypted_email != member.email and db.query(Member).filter(Member.email == encrypted_email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        member.email = encrypted_email
    
    db.commit()
    db.refresh(member)
    return {
        "id": member.id,
        "name": member.name,
        "phone": member.phone,
        "email": member.email,
        "join_date": member.join_date
    }