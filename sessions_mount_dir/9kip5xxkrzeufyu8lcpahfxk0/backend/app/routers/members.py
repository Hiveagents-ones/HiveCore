from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ..database import get_db, Member, MemberCard
from ..utils.member_level import calculate_member_level
from ..utils.bulk_import import process_member_import

router = APIRouter(
    prefix="/api/v1/members",
    tags=["members"]
)


@router.get("/", response_model=List[dict])
def get_members(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get all members with pagination
    """
    members = db.query(Member).offset(skip).limit(limit).all()
    return [{
        "id": member.id,
        "name": member.name,
        "phone": member.phone,
        "email": member.email,
        "join_date": member.join_date
    } for member in members]


@router.post("/", response_model=dict)
def create_member(member_data: dict, db: Session = Depends(get_db)):
    """
    Create a new member
    """
    try:
        new_member = Member(
            name=member_data["name"],
            phone=member_data["phone"],
            email=member_data["email"],
            join_date=datetime.utcnow()
        )
        db.add(new_member)
        db.commit()
        db.refresh(new_member)
        return {
            "id": new_member.id,
            "name": new_member.name,
            "phone": new_member.phone,
            "email": new_member.email,
            "join_date": new_member.join_date
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{member_id}", response_model=dict)
def get_member(member_id: int, db: Session = Depends(get_db)):
    """
    Get a specific member by ID
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return {
        "id": member.id,
        "name": member.name,
        "phone": member.phone,
        "email": member.email,
        "join_date": member.join_date
    }


@router.put("/{member_id}", response_model=dict)
def update_member(member_id: int, member_data: dict, db: Session = Depends(get_db)):
    """
    Update a member's information
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    try:
        member.name = member_data.get("name", member.name)
        member.phone = member_data.get("phone", member.phone)
        member.email = member_data.get("email", member.email)
        db.commit()
        db.refresh(member)
        return {
            "id": member.id,
            "name": member.name,
            "phone": member.phone,
            "email": member.email,
            "join_date": member.join_date
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{member_id}")


@router.post("/bulk-import", response_model=dict)
def bulk_import_members(import_data: dict, db: Session = Depends(get_db)):
    """
    Bulk import members from external data
    """
    try:
        result = process_member_import(import_data, db)
        return {
            "success": True,
            "imported_count": result["imported_count"],
            "skipped_count": result["skipped_count"],
            "errors": result["errors"]
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
def delete_member(member_id: int, db: Session = Depends(get_db)):
    """
    Delete a member
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    try:
        db.delete(member)
        db.commit()
        return {"message": "Member deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{member_id}/cards", response_model=List[dict])


@router.get("/{member_id}/level", response_model=dict)
def get_member_level(member_id: int, db: Session = Depends(get_db)):
    """
    Calculate and get a member's level based on their activity
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Get all cards for the member
    cards = db.query(MemberCard).filter(MemberCard.member_id == member_id).all()
    
    # Calculate level based on membership duration and card status
    level_info = calculate_member_level(member.join_date, cards)
    
    return {
        "member_id": member_id,
        "level": level_info["level"],
        "points": level_info["points"],
        "next_level": level_info["next_level"],
        "progress": level_info["progress"]
    }
def get_member_cards(member_id: int, db: Session = Depends(get_db)):
    """
    Get all cards for a specific member
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    cards = db.query(MemberCard).filter(MemberCard.member_id == member_id).all()
    return [{
        "id": card.id,
        "card_number": card.card_number,
        "expiry_date": card.expiry_date,
        "status": card.status
    } for card in cards]


@router.post("/{member_id}/cards", response_model=dict)
def create_member_card(member_id: int, card_data: dict, db: Session = Depends(get_db)):
    """
    Create a new card for a member
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    try:
        new_card = MemberCard(
            member_id=member_id,
            card_number=card_data["card_number"],
            expiry_date=card_data["expiry_date"],
            status=card_data.get("status", "active")
        )
        db.add(new_card)
        db.commit()
        db.refresh(new_card)
        return {
            "id": new_card.id,
            "card_number": new_card.card_number,
            "expiry_date": new_card.expiry_date,
            "status": new_card.status
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{member_id}/cards/{card_id}", response_model=dict)
def update_member_card(
    member_id: int, 
    card_id: int, 
    card_data: dict, 
    db: Session = Depends(get_db)
):
    """
    Update a member's card
    """
    card = db.query(MemberCard).filter(
        MemberCard.id == card_id,
        MemberCard.member_id == member_id
    ).first()
    
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    try:
        card.card_number = card_data.get("card_number", card.card_number)
        card.expiry_date = card_data.get("expiry_date", card.expiry_date)
        card.status = card_data.get("status", card.status)
        db.commit()
        db.refresh(card)
        return {
            "id": card.id,
            "card_number": card.card_number,
            "expiry_date": card.expiry_date,
            "status": card.status
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))