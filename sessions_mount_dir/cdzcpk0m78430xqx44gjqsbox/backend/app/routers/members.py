from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db, Member, Booking

router = APIRouter(
    prefix="/api/v1/members",
    tags=["members"]
)


@router.get("/", response_model=List[dict])
def list_members(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    获取会员列表
    - skip: 跳过记录数
    - limit: 每页记录数
    """
    members = db.query(Member).offset(skip).limit(limit).all()
    return [{
        "id": member.id,
        "name": member.name,
        "phone": member.phone,
        "email": member.email,
        "card_status": member.card_status,
        "join_date": member.join_date,
        "address": member.address,
        "emergency_contact": member.emergency_contact
    } for member in members]


@router.post("/", response_model=dict)
def create_member(member_data: dict, db: Session = Depends(get_db)):
    """
    创建新会员
    """
    db_member = Member(
        name=member_data["name"],
        phone=member_data["phone"],
        email=member_data["email"],
        card_status=member_data.get("card_status", "active"),
        join_date=member_data["join_date"],
        address=member_data.get("address", ""),
        emergency_contact=member_data.get("emergency_contact", "")
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return {
        "id": db_member.id,
        "name": db_member.name,
        "phone": db_member.phone,
        "email": db_member.email,
        "card_status": db_member.card_status,
        "join_date": db_member.join_date,
        "address": db_member.address,
        "emergency_contact": db_member.emergency_contact
    }


@router.get("/{member_id}", response_model=dict)
def get_member(member_id: int, db: Session = Depends(get_db)):
    """
    获取会员详情
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    bookings = db.query(Booking).filter(Booking.member_id == member_id).all()
    
    return {
        "id": member.id,
        "name": member.name,
        "phone": member.phone,
        "email": member.email,
        "card_status": member.card_status,
        "bookings": [{
            "id": booking.id,
            "course_id": booking.course_id,
            "booking_time": booking.booking_time,
            "status": booking.status
        } for booking in bookings]
    }


@router.put("/{member_id}", response_model=dict)
def update_member(member_id: int, member_data: dict, db: Session = Depends(get_db)):
    """
    更新会员信息
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    if "name" in member_data:
        member.name = member_data["name"]
    if "phone" in member_data:
        member.phone = member_data["phone"]
    if "email" in member_data:
        member.email = member_data["email"]
    if "card_status" in member_data:
        member.card_status = member_data["card_status"]
    
    db.commit()
    db.refresh(member)
    
    return {
        "id": member.id,
        "name": member.name,
        "phone": member.phone,
        "email": member.email,
        "card_status": member.card_status
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

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
@router.get("/{member_id}", response_model=dict)
def get_member(member_id: int, db: Session = Depends(get_db)):
    """
    获取会员详情
    - member_id: 会员ID
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    bookings = db.query(Booking).filter(Booking.member_id == member_id).all()

    return {
        "id": member.id,
        "name": member.name,
        "phone": member.phone,
        "email": member.email,
        "card_status": member.card_status,
        "bookings": [{
            "id": booking.id,
            "course_id": booking.course_id,
            "booking_time": booking.booking_time,
            "status": booking.status
        } for booking in bookings]
    }