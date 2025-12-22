from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.member import Member
from app.schemas.member import MemberCreate, MemberResponse

router = APIRouter()

@router.post("/register", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def register_member(member_data: MemberCreate, db: Session = Depends(get_db)):
    """
    Register a new gym member
    """
    # Check if member with same phone or ID already exists
    existing_member = db.query(Member).filter(
        (Member.phone == member_data.phone) | 
        (Member.id_card == member_data.id_card)
    ).first()
    
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Member with this phone number or ID card already exists"
        )
    
    # Create new member
    new_member = Member(
        name=member_data.name,
        phone=member_data.phone,
        id_card=member_data.id_card
    )
    
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    
    return new_member

@router.get("/{member_id}", response_model=MemberResponse)
def get_member(member_id: int, db: Session = Depends(get_db)):
    """
    Get member details by ID
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    return member

@router.get("/", response_model=List[MemberResponse])
def list_members(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    List all members with pagination
    """
    members = db.query(Member).offset(skip).limit(limit).all()
    return members

@router.get("/phone/{phone}", response_model=MemberResponse)
def get_member_by_phone(phone: str, db: Session = Depends(get_db)):
    """
    Get member details by phone number
    """
    member = db.query(Member).filter(Member.phone == phone).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    return member
