from sqlalchemy.orm import Session
from ..models.member import Member, MemberCard
from ..schemas.member import MemberProfile, MemberProfileUpdate

def create_member_card(db: Session, member_id: int, card_type: str, expiry_date: str):
    db_card = MemberCard(member_id=member_id, card_type=card_type, expiry_date=expiry_date, status="inactive")
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card

def update_card_status(db: Session, card_id: int, status: str):
    db_card = db.query(MemberCard).filter(MemberCard.id == card_id).first()
    if db_card:
        db_card.status = status
        db.commit()
        db.refresh(db_card)
    return db_card

def renew_card(db: Session, card_id: int, new_expiry_date: str):
    db_card = db.query(MemberCard).filter(MemberCard.id == card_id).first()
    if db_card:
        db_card.expiry_date = new_expiry_date
        db.commit()
        db.refresh(db_card)
    return db_card

def get_member_cards(db: Session, member_id: int):
    return db.query(MemberCard).filter(MemberCard.member_id == member_id).all()