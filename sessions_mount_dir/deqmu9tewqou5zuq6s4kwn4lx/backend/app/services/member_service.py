import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..models import Member
from ..core.security import encrypt_sensitive_data

logger = logging.getLogger(__name__)

class MemberService:
    @staticmethod
    def generate_unique_member_id() -> str:
        """Generate a unique member ID using UUID"""
        return f"MBR-{uuid.uuid4().hex[:8].upper()}"

    @staticmethod
    def register_member(
        db: Session,
        name: str,
        phone: str,
        id_card: str,
        email: Optional[str] = None
    ) -> Member:
        """Register a new member with encrypted sensitive data"""
        try:
            # Check if phone number already exists
            existing_member = db.query(Member).filter(Member.phone == phone).first()
            if existing_member:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already registered"
                )

            # Check if email already exists (if provided)
            if email:
                existing_email = db.query(Member).filter(Member.email == email).first()
                if existing_email:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already registered"
                    )

            # Generate unique member ID
            member_id = MemberService.generate_unique_member_id()
            
            # Ensure member_id is unique
            while db.query(Member).filter(Member.member_id == member_id).first():
                member_id = MemberService.generate_unique_member_id()

            # Create new member instance
            new_member = Member(
                member_id=member_id,
                name=name,
                phone=phone,
                email=email
            )
            
            # Encrypt and set ID card
            new_member.set_id_card(id_card)

            # Save to database
            db.add(new_member)
            db.commit()
            db.refresh(new_member)

            logger.info(f"New member registered: {member_id}")
            return new_member

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error registering member: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to register member"
            )

    @staticmethod
    def get_member_by_id(db: Session, member_id: str) -> Optional[Member]:
        """Retrieve member by member ID"""
        try:
            member = db.query(Member).filter(Member.member_id == member_id).first()
            if member:
                logger.info(f"Retrieved member: {member_id}")
            return member
        except Exception as e:
            logger.error(f"Error retrieving member {member_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve member"
            )

    @staticmethod
    def get_member_by_phone(db: Session, phone: str) -> Optional[Member]:
        """Retrieve member by phone number"""
        try:
            member = db.query(Member).filter(Member.phone == phone).first()
            if member:
                logger.info(f"Retrieved member by phone: {phone}")
            return member
        except Exception as e:
            logger.error(f"Error retrieving member by phone {phone}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve member"
            )

    @staticmethod
    def update_member(
        db: Session,
        member_id: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        id_card: Optional[str] = None
    ) -> Member:
        """Update member information"""
        try:
            member = db.query(Member).filter(Member.member_id == member_id).first()
            if not member:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Member not found"
                )

            # Update fields if provided
            if name is not None:
                member.name = name
            if phone is not None:
                # Check if new phone already exists
                existing = db.query(Member).filter(
                    Member.phone == phone,
                    Member.id != member.id
                ).first()
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Phone number already registered"
                    )
                member.phone = phone
            if email is not None:
                # Check if new email already exists
                if email:
                    existing = db.query(Member).filter(
                        Member.email == email,
                        Member.id != member.id
                    ).first()
                    if existing:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Email already registered"
                        )
                member.email = email
            if id_card is not None:
                member.set_id_card(id_card)

            member.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(member)

            logger.info(f"Updated member: {member_id}")
            return member

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating member {member_id}: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update member"
            )

    @staticmethod
    def deactivate_member(db: Session, member_id: str) -> Member:
        """Deactivate a member account"""
        try:
            member = db.query(Member).filter(Member.member_id == member_id).first()
            if not member:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Member not found"
                )

            member.is_active = False
            member.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(member)

            logger.info(f"Deactivated member: {member_id}")
            return member

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deactivating member {member_id}: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate member"
            )

    @staticmethod
    def get_member_summary(member: Member) -> Dict[str, Any]:
        """Get member summary without sensitive data"""
        return {
            "member_id": member.member_id,
            "name": member.name,
            "phone": member.phone,
            "email": member.email,
            "is_active": member.is_active,
            "created_at": member.created_at,
            "updated_at": member.updated_at
        }
