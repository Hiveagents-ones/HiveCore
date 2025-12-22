from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.member import Member, MemberStatus
from app.schemas.member import MemberCreate, MemberUpdate

def get_member(db: Session, member_id: int) -> Optional[Member]:
    """
    Retrieve a single member by ID.
    """
    return db.query(Member).filter(Member.id == member_id).first()

def get_member_by_card_number(db: Session, card_number: str) -> Optional[Member]:
    """
    Retrieve a single member by card number.
    """
    return db.query(Member).filter(Member.card_number == card_number).first()

def get_members(db: Session, skip: int = 0, limit: int = 100) -> List[Member]:
    """
    Retrieve a list of members with pagination.
    """
    return db.query(Member).offset(skip).limit(limit).all()

def create_member(db: Session, member: MemberCreate) -> Member:
    """
    Create a new member.
    """
    db_member = Member(
        name=member.name,
        contact=member.contact,
        card_number=member.card_number,
        level=member.level,
        status=member.status
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

def update_member(db: Session, member_id: int, member: MemberUpdate) -> Optional[Member]:
    """
    Update an existing member.
    """
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if not db_member:
        return None
    
    update_data = member.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_member, field, value)
    
    db.commit()
    db.refresh(db_member)
    return db_member

def delete_member(db: Session, member_id: int) -> Optional[Member]:
    """
    Delete a member by ID.
    """
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if not db_member:
        return None
    
    db.delete(db_member)
    db.commit()
    return db_member

def get_members_by_status(db: Session, status: MemberStatus, skip: int = 0, limit: int = 100) -> List[Member]:
    """
    Retrieve members filtered by status.
    """
    return db.query(Member).filter(Member.status == status).offset(skip).limit(limit).all()
