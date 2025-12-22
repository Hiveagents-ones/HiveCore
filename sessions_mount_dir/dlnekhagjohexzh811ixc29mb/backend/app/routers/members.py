from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db, Member
from ..schemas import MemberCreate, MemberUpdate, MemberResponse

router = APIRouter(
    prefix="/api/v1/members",
    tags=["members"]
)

@router.post("/", response_model=MemberResponse)
def create_member(member: MemberCreate, db: Session = Depends(get_db)):
    """
    Create a new member
    """
    # Check if phone or email already exists
    existing_phone = db.query(Member).filter(Member.phone == member.phone).first()
    if existing_phone:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    existing_email = db.query(Member).filter(Member.email == member.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_member = Member(
        name=member.name,
        phone=member.phone,
        email=member.email,
        membership_type=member.membership_type
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

@router.get("/", response_model=List[MemberResponse])
def read_members(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve all members with pagination
    """
    members = db.query(Member).offset(skip).limit(limit).all()
    return members

@router.get("/{member_id}", response_model=MemberResponse)
def read_member(member_id: int, db: Session = Depends(get_db)):
    """
    Get a specific member by ID
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return member

@router.put("/{member_id}", response_model=MemberResponse)
def update_member(member_id: int, member: MemberUpdate, db: Session = Depends(get_db)):
    """
    Update a member's information
    """
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if db_member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Check if new phone or email conflicts with existing records
    if member.phone and member.phone != db_member.phone:
        existing_phone = db.query(Member).filter(Member.phone == member.phone).first()
        if existing_phone:
            raise HTTPException(status_code=400, detail="Phone number already registered")
    
    if member.email and member.email != db_member.email:
        existing_email = db.query(Member).filter(Member.email == member.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Update fields
    if member.name:
        db_member.name = member.name
    if member.phone:
        db_member.phone = member.phone
    if member.email:
        db_member.email = member.email
    if member.membership_type:
        db_member.membership_type = member.membership_type
    
    db.commit()
    db.refresh(db_member)
    return db_member