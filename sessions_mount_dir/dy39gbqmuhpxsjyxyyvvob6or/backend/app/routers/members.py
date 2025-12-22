from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ..database import get_db, Member
from ..schemas.member import MemberCreate, MemberUpdate, MemberOut, MemberWithStatus

router = APIRouter(
    prefix="/api/v1/members",
    tags=["members"]
)

@router.get("/", response_model=List[MemberWithStatus])
def list_members(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    获取会员列表
    """
    members = db.query(Member).offset(skip).limit(limit).all()
    return [{
        "id": member.id,
        "name": member.name,
        "email": member.email,
        "phone": member.phone,
        "join_date": member.join_date,
        "age": member.age,
        "gender": member.gender,
        "address": member.address,
        "emergency_contact": member.emergency_contact,
        "membership_type": member.membership_type,
        "membership_expiry": member.membership_expiry,
        "status": "active" if member.membership_expiry and member.membership_expiry > datetime.now() else "inactive"
    } for member in members]

@router.post("/", response_model=MemberOut)
def create_member(member: MemberCreate, db: Session = Depends(get_db)):
    """
    创建新会员
    """
    db_member = Member(
        name=member.name,
        email=member.email,
        phone=member.phone,
        join_date=datetime.now(),
        age=member.age if hasattr(member, 'age') else None,
        gender=member.gender if hasattr(member, 'gender') else None,
        address=member.address if hasattr(member, 'address') else None,
        emergency_contact=member.emergency_contact if hasattr(member, 'emergency_contact') else None,
        membership_type=member.membership_type if hasattr(member, 'membership_type') else 'regular',
        membership_expiry=member.membership_expiry if hasattr(member, 'membership_expiry') else None
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return {
        "id": db_member.id,
        "name": db_member.name,
        "email": db_member.email,
        "phone": db_member.phone,
        "join_date": db_member.join_date
    }

@router.get("/{member_id}", response_model=MemberWithStatus)
def get_member(member_id: int, db: Session = Depends(get_db)):
    """
    获取单个会员详情
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return {
        "id": member.id,
        "name": member.name,
        "email": member.email,
        "phone": member.phone,
        "join_date": member.join_date,
        "age": member.age,
        "gender": member.gender,
        "address": member.address,
        "emergency_contact": member.emergency_contact,
        "membership_type": member.membership_type,
        "membership_expiry": member.membership_expiry,
        "status": "active" if member.membership_expiry and member.membership_expiry > datetime.now() else "inactive"
    }

@router.put("/{member_id}", response_model=MemberWithStatus)
def update_member(member_id: int, member_data: MemberUpdate, db: Session = Depends(get_db)):
    """
    更新会员信息
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    if member_data.name is not None:
        member.name = member_data.name
    if member_data.email is not None:
        member.email = member_data.email
    if member_data.phone is not None:
        member.phone = member_data.phone
    if hasattr(member_data, 'age') and member_data.age is not None:
        member.age = member_data.age
    if hasattr(member_data, 'gender') and member_data.gender is not None:
        member.gender = member_data.gender
    if hasattr(member_data, 'address') and member_data.address is not None:
        member.address = member_data.address
    if hasattr(member_data, 'emergency_contact') and member_data.emergency_contact is not None:
        member.emergency_contact = member_data.emergency_contact
    if hasattr(member_data, 'membership_type') and member_data.membership_type is not None:
        member.membership_type = member_data.membership_type
    if hasattr(member_data, 'membership_expiry') and member_data.membership_expiry is not None:
        member.membership_expiry = member_data.membership_expiry
    
    db.commit()
    db.refresh(member)
    return {
        "id": member.id,
        "name": member.name,
        "email": member.email,
        "phone": member.phone,
        "join_date": member.join_date
    }

@router.delete("/{member_id}")
def delete_member(member_id: int, db: Session = Depends(get_db)):
    """
    删除会员
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    db.delete(member)
    db.commit()
    return {"message": "Member deleted successfully"}