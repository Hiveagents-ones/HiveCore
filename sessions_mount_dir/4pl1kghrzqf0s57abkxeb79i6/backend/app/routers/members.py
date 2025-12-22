from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from ..database import get_db
from ..models import Member as MemberModel, MemberCard as MemberCardModel, AccessRecord as AccessRecordModel
from ..schemas import (
    Member, MemberCreate, MemberUpdate,
    MemberCard, MemberCardCreate, MemberCardUpdate,
    AccessRecord, AccessRecordCreate,
    MemberBatchImport, MemberBatchExport,
    MembershipRenewal, MembershipTypeEnum, MembershipStatusEnum
)

router = APIRouter(prefix="/api/v1/members", tags=["members"])

# Helper function to calculate membership end date based on type
def calculate_membership_end_date(membership_type: MembershipTypeEnum, start_date: datetime) -> datetime:
    if membership_type == MembershipTypeEnum.monthly:
        return start_date + timedelta(days=30)
    elif membership_type == MembershipTypeEnum.quarterly:
        return start_date + timedelta(days=90)
    elif membership_type == MembershipTypeEnum.yearly:
        return start_date + timedelta(days=365)
    else:
        raise ValueError("Invalid membership type")

# CRUD operations for members
@router.post("/", response_model=Member, status_code=status.HTTP_201_CREATED)
def create_member(member: MemberCreate, db: Session = Depends(get_db)):
    db_member = db.query(MemberModel).filter(MemberModel.phone == member.phone).first()
    if db_member:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    if member.email:
        db_member = db.query(MemberModel).filter(MemberModel.email == member.email).first()
        if db_member:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    membership_start = datetime.utcnow()
    membership_end = member.membership_end or calculate_membership_end_date(member.membership_type, membership_start)
    
    db_member = MemberModel(
        **member.dict(),
        membership_start=membership_start,
        membership_end=membership_end
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

@router.get("/", response_model=List[Member])
def list_members(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    members = db.query(MemberModel).offset(skip).limit(limit).all()
    return members

@router.get("/{member_id}", response_model=Member)
def get_member(member_id: int, db: Session = Depends(get_db)):
    member = db.query(MemberModel).filter(MemberModel.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member

@router.put("/{member_id}", response_model=Member)
def update_member(member_id: int, member_update: MemberUpdate, db: Session = Depends(get_db)):
    db_member = db.query(MemberModel).filter(MemberModel.id == member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    update_data = member_update.dict(exclude_unset=True)
    
    # Check for phone/email conflicts if they are being updated
    if "phone" in update_data:
        existing_member = db.query(MemberModel).filter(MemberModel.phone == update_data["phone"]).first()
        if existing_member and existing_member.id != member_id:
            raise HTTPException(status_code=400, detail="Phone number already registered")
    
    if "email" in update_data and update_data["email"]:
        existing_member = db.query(MemberModel).filter(MemberModel.email == update_data["email"]).first()
        if existing_member and existing_member.id != member_id:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # If membership type is being updated, recalculate end date
    if "membership_type" in update_data and "membership_end" not in update_data:
        update_data["membership_end"] = calculate_membership_end_date(
            update_data["membership_type"],
            db_member.membership_start
        )
    
    for key, value in update_data.items():
        setattr(db_member, key, value)
    
    db.commit()
    db.refresh(db_member)
    return db_member

@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(member_id: int, db: Session = Depends(get_db)):
    db_member = db.query(MemberModel).filter(MemberModel.id == member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    db.delete(db_member)
    db.commit()
    return None

# Member card operations
@router.post("/{member_id}/cards", response_model=MemberCard, status_code=status.HTTP_201_CREATED)
def create_member_card(member_id: int, card: MemberCardCreate, db: Session = Depends(get_db)):
    db_member = db.query(MemberModel).filter(MemberModel.id == member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    db_card = db.query(MemberCardModel).filter(MemberCardModel.card_number == card.card_number).first()
    if db_card:
        raise HTTPException(status_code=400, detail="Card number already exists")
    
    db_card = MemberCardModel(**card.dict(), member_id=member_id)
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card

@router.get("/{member_id}/cards", response_model=List[MemberCard])
def list_member_cards(member_id: int, db: Session = Depends(get_db)):
    db_member = db.query(MemberModel).filter(MemberModel.id == member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    cards = db.query(MemberCardModel).filter(MemberCardModel.member_id == member_id).all()
    return cards

@router.put("/cards/{card_id}", response_model=MemberCard)
def update_member_card(card_id: int, card_update: MemberCardUpdate, db: Session = Depends(get_db)):
    db_card = db.query(MemberCardModel).filter(MemberCardModel.id == card_id).first()
    if not db_card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    update_data = card_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_card, key, value)
    
    db.commit()
    db.refresh(db_card)
    return db_card

@router.delete("/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member_card(card_id: int, db: Session = Depends(get_db)):
    db_card = db.query(MemberCardModel).filter(MemberCardModel.id == card_id).first()
    if not db_card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    db.delete(db_card)
    db.commit()
    return None

# Access record operations
@router.post("/{member_id}/access", response_model=AccessRecord, status_code=status.HTTP_201_CREATED)
def create_access_record(member_id: int, access: AccessRecordCreate, db: Session = Depends(get_db)):
    db_member = db.query(MemberModel).filter(MemberModel.id == member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    db_access = AccessRecordModel(**access.dict(), member_id=member_id)
    db.add(db_access)
    db.commit()
    db.refresh(db_access)
    return db_access

@router.get("/{member_id}/access", response_model=List[AccessRecord])
def list_access_records(member_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    db_member = db.query(MemberModel).filter(MemberModel.id == member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    records = db.query(AccessRecordModel).filter(AccessRecordModel.member_id == member_id).offset(skip).limit(limit).all()
    return records

# Batch operations
@router.post("/batch/import", response_model=List[Member], status_code=status.HTTP_201_CREATED)
def batch_import_members(batch: MemberBatchImport, db: Session = Depends(get_db)):
    created_members = []
    for member_data in batch.members:
        # Check for duplicates
        db_member = db.query(MemberModel).filter(MemberModel.phone == member_data.phone).first()
        if db_member:
            continue  # Skip existing members
        
        if member_data.email:
            db_member = db.query(MemberModel).filter(MemberModel.email == member_data.email).first()
            if db_member:
                continue  # Skip existing members
        
        membership_start = datetime.utcnow()
        membership_end = member_data.membership_end or calculate_membership_end_date(member_data.membership_type, membership_start)
        
        db_member = MemberModel(
            **member_data.dict(),
            membership_start=membership_start,
            membership_end=membership_end
        )
        db.add(db_member)
        created_members.append(db_member)
    
    db.commit()
    for member in created_members:
        db.refresh(member)
    
    return created_members

@router.post("/batch/export")
def batch_export_members(batch: MemberBatchExport, db: Session = Depends(get_db)):
    members = db.query(MemberModel).filter(MemberModel.id.in_(batch.member_ids)).all()
    if not members:
        raise HTTPException(status_code=404, detail="No members found with the provided IDs")
    
    # In a real implementation, this would generate and return a file
    # For now, we'll just return the member data
    return {"members": members, "exported_at": datetime.utcnow()}

# Membership renewal
@router.post("/{member_id}/renew", response_model=Member)
def renew_membership(member_id: int, renewal: MembershipRenewal, db: Session = Depends(get_db)):
    db_member = db.query(MemberModel).filter(MemberModel.id == member_id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Calculate new end date
    if db_member.membership_end and db_member.membership_end > datetime.utcnow():
        # Extend from current end date
        new_end_date = calculate_membership_end_date(renewal.membership_type, db_member.membership_end)
    else:
        # Start from today
        new_end_date = calculate_membership_end_date(renewal.membership_type, datetime.utcnow())
    
    db_member.membership_type = renewal.membership_type
    db_member.membership_end = new_end_date
    db_member.membership_status = MembershipStatusEnum.active
    
    db.commit()
    db.refresh(db_member)
    return db_member
