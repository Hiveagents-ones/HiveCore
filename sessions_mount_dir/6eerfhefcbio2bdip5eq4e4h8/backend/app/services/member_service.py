from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from ..models import Member

class MemberService:
    def __init__(self, db: Session):
        self.db = db

    def calculate_expiry_date(self, level: str, effective_date: Optional[datetime] = None) -> datetime:
        """
        Calculate expiry date based on membership level
        
        Args:
            level: Membership level (e.g., 'basic', 'premium', 'vip')
            effective_date: When the membership becomes effective (defaults to now)
            
        Returns:
            datetime: The calculated expiry date
        """
        if effective_date is None:
            effective_date = datetime.utcnow()
            
        # Define duration for each membership level (in days)
        level_durations = {
            'basic': 30,
            'silver': 90,
            'gold': 180,
            'platinum': 365,
            'vip': 365
        }
        
        duration = level_durations.get(level.lower(), 30)  # Default to 30 days if level not found
        return effective_date + timedelta(days=duration)

    def create_member(self, name: str, contact: str, level: str, 
                     effective_date: Optional[datetime] = None,
                     custom_fields: Optional[dict] = None) -> Member:
        """
        Create a new member with automatic expiry date calculation
        
        Args:
            name: Member's name
            contact: Member's contact information
            level: Membership level
            effective_date: When the membership becomes effective
            custom_fields: Additional custom fields
            
        Returns:
            Member: The created member instance
        """
        expiry_date = self.calculate_expiry_date(level, effective_date)
        
        member = Member(
            name=name,
            contact=contact,
            level=level,
            effective_date=effective_date or datetime.utcnow(),
            expiry_date=expiry_date,
            custom_fields=custom_fields
        )
        
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member

    def update_member_level(self, member_id: int, new_level: str) -> Optional[Member]:
        """
        Update member's level and recalculate expiry date
        
        Args:
            member_id: ID of the member to update
            new_level: New membership level
            
        Returns:
            Member: Updated member instance or None if not found
        """
        member = self.db.query(Member).filter(Member.id == member_id).first()
        if not member:
            return None
            
        member.level = new_level
        member.expiry_date = self.calculate_expiry_date(new_level, member.effective_date)
        member.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(member)
        return member

    def get_member(self, member_id: int) -> Optional[Member]:
        """
        Get member by ID
        
        Args:
            member_id: ID of the member
            
        Returns:
            Member: Member instance or None if not found
        """
        return self.db.query(Member).filter(Member.id == member_id).first()

    def get_all_members(self, skip: int = 0, limit: int = 100) -> list[Member]:
        """
        Get all members with pagination
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            list[Member]: List of member instances
        """
        return self.db.query(Member).offset(skip).limit(limit).all()

    def delete_member(self, member_id: int) -> bool:
        """
        Delete a member by ID
        
        Args:
            member_id: ID of the member to delete
            
        Returns:
            bool: True if deleted, False if not found
        """
        member = self.db.query(Member).filter(Member.id == member_id).first()
        if not member:
            return False
            
        self.db.delete(member)
        self.db.commit()
        return True

    def update_member(self, member_id: int, **kwargs) -> Optional[Member]:
        """
        Update member information
        
        Args:
            member_id: ID of the member to update
            **kwargs: Fields to update
            
        Returns:
            Member: Updated member instance or None if not found
        """
        member = self.db.query(Member).filter(Member.id == member_id).first()
        if not member:
            return None
            
        # If level is being updated, recalculate expiry date
        if 'level' in kwargs:
            kwargs['expiry_date'] = self.calculate_expiry_date(
                kwargs['level'], 
                kwargs.get('effective_date', member.effective_date)
            )
            
        for key, value in kwargs.items():
            if hasattr(member, key):
                setattr(member, key, value)
                
        member.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(member)
        return member
