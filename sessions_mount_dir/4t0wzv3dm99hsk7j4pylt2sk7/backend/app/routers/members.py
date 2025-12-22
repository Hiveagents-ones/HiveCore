from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import User, Member
from ..schemas import Member as MemberSchema, MemberCreate, MemberUpdate
from ..core.security import get_current_user, require_permission, require_ownership_or_permission

router = APIRouter(prefix="/members", tags=["members"])

@router.get("/", response_model=List[MemberSchema])
def get_members(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ownership_or_permission("members", "read"))
):
    # If user is a coach, only show members they are responsible for
    if "coach" in [role.name for role in current_user.roles]:
        members = db.query(Member).filter(Member.coach_id == current_user.id).offset(skip).limit(limit).all()
    else:
        members = db.query(Member).offset(skip).limit(limit).all()
    return members

@router.post("/", response_model=MemberSchema)
def create_member(
    member: MemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("members", "create"))
):
    db_member = Member(**member.model_dump())
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

@router.get("/{member_id}", response_model=MemberSchema)
def get_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ownership_or_permission("members", "read"))
):
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Check if user is the coach of this member
    if "coach" in [role.name for role in current_user.roles] and db_member.coach_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this member")
    
    return db_member

@router.put("/{member_id}", response_model=MemberSchema)
def update_member(
    member_id: int,
    member_update: MemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ownership_or_permission("members", "update"))
):
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Check if user is the coach of this member
    if "coach" in [role.name for role in current_user.roles] and db_member.coach_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this member")
    
    update_data = member_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_member, field, value)
    
    db.commit()
    db.refresh(db_member)
    return db_member

@router.delete("/{member_id}")
def delete_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ownership_or_permission("members", "delete"))
):
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Check if user is the coach of this member
    if "coach" in [role.name for role in current_user.roles] and db_member.coach_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this member")
    
    db.delete(db_member)
    db.commit()
    return {"message": "Member deleted successfully"}

@router.get("/coach/my-members", response_model=List[MemberSchema])
def get_my_members(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user is a coach
    if "coach" not in [role.name for role in current_user.roles]:
        raise HTTPException(status_code=403, detail="User is not a coach")
    
    members = db.query(Member).filter(Member.coach_id == current_user.id).all()
    return members