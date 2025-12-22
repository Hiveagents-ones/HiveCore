from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Member
from ..schemas import MemberCreate, MemberUpdate, MemberResponse

router = APIRouter()

@router.get("/", response_model=List[MemberResponse])
def list_members(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve a list of members with pagination support.
    
    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        db: Database session dependency
    
    Returns:
        List of MemberResponse objects
    """
    members = db.query(Member).offset(skip).limit(limit).all()
    return members

@router.post("/", response_model=MemberResponse, status_code=201)
def create_member(member: MemberCreate, db: Session = Depends(get_db)):
    """
    Create a new member record.
    
    Args:
        member: Member data to create
        db: Database session dependency
    
    Returns:
        Created MemberResponse object
    """
    db_member = Member(**member.dict())
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

@router.get("/{member_id}", response_model=MemberResponse)
def get_member(member_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a single member by ID.
    
    Args:
        member_id: ID of the member to retrieve
        db: Database session dependency
    
    Returns:
        MemberResponse object
    
    Raises:
        HTTPException: 404 if member not found
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member

@router.put("/{member_id}", response_model=MemberResponse)
def update_member(member_id: int, member: MemberUpdate, db: Session = Depends(get_db)):
    """
    Update an existing member record.
    
    Args:
        member_id: ID of the member to update
        member: Updated member data
        db: Database session dependency
    
    Returns:
        Updated MemberResponse object
    
    Raises:
        HTTPException: 404 if member not found
    """
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    update_data = member.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_member, key, value)
    
    db.commit()
    db.refresh(db_member)
    return db_member

@router.delete("/{member_id}", status_code=204)
def delete_member(member_id: int, db: Session = Depends(get_db)):
    """
    Delete a member record.
    
    Args:
        member_id: ID of the member to delete
        db: Database session dependency
    
    Returns:
        None (204 No Content)
    
    Raises:
        HTTPException: 404 if member not found
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    db.delete(member)
    db.commit()
    return None