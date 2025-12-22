from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..schemas.member import MemberCardCreate, MemberCardUpdate, MemberCardResponse
from ..crud.member import create_member_card, update_card_status, renew_card, get_member_cards
from ..database import get_db

router = APIRouter(prefix="/api/members", tags=["Member Cards"])

@router.post("/cards/create", response_model=MemberCardResponse)
def create_card(card: MemberCardCreate, db: Session = Depends(get_db)):
    return create_member_card(db, card.member_id, card.card_type, card.expiry_date)

@router.post("/cards/{card_id}/activate", response_model=MemberCardResponse)
def activate_card(card_id: int, db: Session = Depends(get_db)):
    return update_card_status(db, card_id, "active")

@router.post("/cards/{card_id}/deactivate", response_model=MemberCardResponse)
def deactivate_card(card_id: int, db: Session = Depends(get_db)):
    return update_card_status(db, card_id, "inactive")

@router.post("/cards/{card_id}/renew", response_model=MemberCardResponse)
def renew_card_endpoint(card_id: int, expiry_date: str, db: Session = Depends(get_db)):
    return renew_card(db, card_id, expiry_date)

@router.get("/cards/{member_id}", response_model=list[MemberCardResponse])
def list_member_cards(member_id: int, db: Session = Depends(get_db)):
    return get_member_cards(db, member_id)