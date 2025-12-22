from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Member, MemberCard
from ..schemas import MemberCardCreate, MemberCardUpdate, MemberCardResponse
from ..enums import MemberCardStatus

router = APIRouter(
    prefix="/api/v1/members",
    tags=["Member Cards"]
)

@router.get("/{member_id}/cards", response_model=List[MemberCardResponse])
def get_member_cards(member_id: int, db: Session = Depends(get_db)):
    """
    Get all cards for a specific member
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member with id {member_id} not found"
        )
    
    return db.query(MemberCard).filter(MemberCard.member_id == member_id).all()

@router.post("/{member_id}/cards", response_model=MemberCardResponse, status_code=status.HTTP_201_CREATED)
def create_member_card(member_id: int, card: MemberCardCreate, db: Session = Depends(get_db)):
    """
    Create a new card for a member
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member with id {member_id} not found"
        )
    
    db_card = MemberCard(**card.dict(), member_id=member_id)
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    
    return db_card

@router.put("/{member_id}/cards/{card_id}", response_model=MemberCardResponse)
@router.put("/{member_id}/cards/{card_id}", response_model=MemberCardResponse)
def update_member_card(
    member_id: int,
    card_id: int,
    card_update: MemberCardUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a member's card information
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member with id {member_id} not found"
        )

    db_card = db.query(MemberCard).filter(
        MemberCard.id == card_id,
        MemberCard.member_id == member_id
    ).first()

    if not db_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Card with id {card_id} not found for member {member_id}"
        )

    for field, value in card_update.dict(exclude_unset=True).items():
        setattr(db_card, field, value)

    db.commit()
    db.refresh(db_card)

    return db_card
@router.delete("/{member_id}/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member_card(
    member_id: int,
    card_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a member's card
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member with id {member_id} not found"
        )

    db_card = db.query(MemberCard).filter(
        MemberCard.id == card_id,
        MemberCard.member_id == member_id
    ).first()

    if not db_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Card with id {card_id} not found for member {member_id}"
        )

    db.delete(db_card)
    db.commit()

    return None
@router.patch("/{member_id}/cards/{card_id}/status", response_model=MemberCardResponse)
def update_member_card_status(
    member_id: int,
    card_id: int,
    status: MemberCardStatus,
    db: Session = Depends(get_db)
):
    """
    Update member card status (active/inactive/expired)
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member with id {member_id} not found"
        )

    db_card = db.query(MemberCard).filter(
        MemberCard.id == card_id,
        MemberCard.member_id == member_id
    ).first()

    if not db_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Card with id {card_id} not found for member {member_id}"
        )

    db_card.status = status
    db.commit()
    db.refresh(db_card)

    return db_card
def update_member_card(
    member_id: int, 
    card_id: int, 
    card_update: MemberCardUpdate, 
    db: Session = Depends(get_db)
):
    """
    Update a member's card information
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member with id {member_id} not found"
        )
    
    db_card = db.query(MemberCard).filter(
        MemberCard.id == card_id,
        MemberCard.member_id == member_id
    ).first()
    
    if not db_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Card with id {card_id} not found for member {member_id}"
        )
    
    for field, value in card_update.dict(exclude_unset=True).items():
        setattr(db_card, field, value)
    
    db.commit()
    db.refresh(db_card)
    
    return db_card