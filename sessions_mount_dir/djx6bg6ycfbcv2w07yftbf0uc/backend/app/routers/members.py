from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import models, schemas, database
from ..database import get_db

router = APIRouter(
    prefix="/members",
    tags=["members"]
)

# Helper function to get member by ID and ensure it belongs to the shop
def get_member_by_id(db: Session, member_id: int, shop_id: int):
    member = db.query(models.Member).filter(
        models.Member.id == member_id,
        models.Member.shop_id == shop_id
    ).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    return member

@router.get("/", response_model=schemas.MemberListResponse)
def list_members(
    shop_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Retrieve a list of members for a specific shop with pagination.
    """
    query = db.query(models.Member).filter(models.Member.shop_id == shop_id)
    total = query.count()
    members = query.offset(skip).limit(limit).all()
    
    # Manually construct the response with details
    members_with_details = []
    for member in members:
        member_data = schemas.MemberWithDetails.from_orm(member)
        member_data.tags = member.tags
        member_data.notes = member.notes
        member_data.consumptions = member.consumptions
        # Assuming appointments are simple dicts for now
        member_data.appointments = [
            {"id": a.id, "date": a.date} for a in member.appointments
        ]
        members_with_details.append(member_data)

    return schemas.MemberListResponse(
        members=members_with_details,
        total=total,
        page=skip // limit + 1,
        per_page=limit
    )

@router.get("/{member_id}", response_model=schemas.MemberWithDetails)
def get_member_details(
    member_id: int,
    shop_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve detailed information for a specific member, including tags, notes, appointments, and consumptions.
    """
    member = get_member_by_id(db, member_id, shop_id)
    
    member_data = schemas.MemberWithDetails.from_orm(member)
    member_data.tags = member.tags
    member_data.notes = member.notes
    member_data.consumptions = member.consumptions
    # Assuming appointments are simple dicts for now
    member_data.appointments = [
        {"id": a.id, "date": a.date} for a in member.appointments
    ]
    
    return member_data

@router.post("/", response_model=schemas.Member, status_code=status.HTTP_201_CREATED)
def create_member(
    member: schemas.MemberCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new member for a shop.
    """
    # Check if phone number already exists for this shop
    db_member = db.query(models.Member).filter(
        models.Member.phone == member.phone,
        models.Member.shop_id == member.shop_id
    ).first()
    if db_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered for this shop"
        )
    
    # Check if email already exists for this shop
    if member.email:
        db_member = db.query(models.Member).filter(
            models.Member.email == member.email,
            models.Member.shop_id == member.shop_id
        ).first()
        if db_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered for this shop"
            )
    
    new_member = models.Member(**member.dict())
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    return new_member

@router.put("/{member_id}", response_model=schemas.Member)
def update_member(
    member_id: int,
    member_update: schemas.MemberUpdate,
    shop_id: int,
    db: Session = Depends(get_db)
):
    """
    Update an existing member's information.
    """
    db_member = get_member_by_id(db, member_id, shop_id)
    
    update_data = member_update.dict(exclude_unset=True)
    
    # Check for unique constraint violations if phone/email is being updated
    if "phone" in update_data:
        existing_member = db.query(models.Member).filter(
            models.Member.phone == update_data["phone"],
            models.Member.shop_id == shop_id,
            models.Member.id != member_id
        ).first()
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered for another member in this shop"
            )
    
    if "email" in update_data and update_data["email"]:
        existing_member = db.query(models.Member).filter(
            models.Member.email == update_data["email"],
            models.Member.shop_id == shop_id,
            models.Member.id != member_id
        ).first()
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered for another member in this shop"
            )
    
    for key, value in update_data.items():
        setattr(db_member, key, value)
    
    db.commit()
    db.refresh(db_member)
    return db_member

@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    member_id: int,
    shop_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a member from a shop.
    """
    db_member = get_member_by_id(db, member_id, shop_id)
    db.delete(db_member)
    db.commit()
    return

# --- Member Tags ---

@router.post("/{member_id}/tags", response_model=schemas.MemberTag, status_code=status.HTTP_201_CREATED)
def add_tag_to_member(
    member_id: int,
    tag: schemas.MemberTagCreate,
    shop_id: int,
    db: Session = Depends(get_db)
):
    """
    Add a new tag to a member.
    """
    get_member_by_id(db, member_id, shop_id) # Ensure member exists and belongs to shop
    
    # Ensure the tag is associated with the correct member and shop
    tag.member_id = member_id
    tag.shop_id = shop_id
    
    new_tag = models.MemberTag(**tag.dict())
    db.add(new_tag)
    db.commit()
    db.refresh(new_tag)
    return new_tag

@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member_tag(
    tag_id: int,
    shop_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a tag from a member.
    """
    tag = db.query(models.MemberTag).filter(
        models.MemberTag.id == tag_id,
        models.MemberTag.shop_id == shop_id
    ).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    db.delete(tag)
    db.commit()
    return

# --- Member Notes ---

@router.post("/{member_id}/notes", response_model=schemas.MemberNote, status_code=status.HTTP_201_CREATED)
def add_note_to_member(
    member_id: int,
    note: schemas.MemberNoteCreate,
    shop_id: int,
    db: Session = Depends(get_db)
):
    """
    Add a new note to a member.
    """
    get_member_by_id(db, member_id, shop_id) # Ensure member exists and belongs to shop
    
    # Ensure the note is associated with the correct member and shop
    note.member_id = member_id
    note.shop_id = shop_id
    
    # TODO: Add validation to ensure staff_id belongs to the same shop
    # staff = db.query(models.Staff).filter(models.Staff.id == note.staff_id, models.Staff.shop_id == shop_id).first()
    # if not staff:
    #     raise HTTPException(status_code=400, detail="Invalid staff for this shop")

    new_note = models.MemberNote(**note.dict())
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return new_note

@router.put("/notes/{note_id}", response_model=schemas.MemberNote)
def update_member_note(
    note_id: int,
    note_update: schemas.MemberNoteBase,
    shop_id: int,
    db: Session = Depends(get_db)
):
    """
    Update an existing member note.
    """
    db_note = db.query(models.MemberNote).filter(
        models.MemberNote.id == note_id,
        models.MemberNote.shop_id == shop_id
    ).first()
    if not db_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )
    
    db_note.content = note_update.content
    db.commit()
    db.refresh(db_note)
    return db_note

@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member_note(
    note_id: int,
    shop_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a member note.
    """
    note = db.query(models.MemberNote).filter(
        models.MemberNote.id == note_id,
        models.MemberNote.shop_id == shop_id
    ).first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )
    db.delete(note)
    db.commit()
    return

# --- Member Consumptions ---

@router.post("/{member_id}/consumptions", response_model=schemas.Consumption, status_code=status.HTTP_201_CREATED)
def add_consumption_for_member(
    member_id: int,
    consumption: schemas.ConsumptionCreate,
    shop_id: int,
    db: Session = Depends(get_db)
):
    """
    Add a new consumption record for a member.
    """
    member = get_member_by_id(db, member_id, shop_id)
    
    # Ensure the consumption is associated with the correct member
    consumption.member_id = member_id
    
    new_consumption = models.Consumption(**consumption.dict())
    db.add(new_consumption)
    
    # Update member's total_spent and visit_count
    member.total_spent += new_consumption.amount
    member.visit_count += 1
    # Optionally update last_visit
    # member.last_visit = datetime.now()
    
    db.commit()
    db.refresh(new_consumption)
    return new_consumption

@router.get("/{member_id}/consumptions", response_model=List[schemas.Consumption])
def list_member_consumptions(
    member_id: int,
    shop_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Retrieve a list of consumption records for a specific member.
    """
    get_member_by_id(db, member_id, shop_id) # Ensure member exists and belongs to shop
    
    consumptions = db.query(models.Consumption).filter(
        models.Consumption.member_id == member_id
    ).offset(skip).limit(limit).all()
    
    return consumptions
