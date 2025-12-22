from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from ....core.security import encrypt_sensitive_data, decrypt_sensitive_data, is_sensitive_field
from ....models import Member
from ....services.member_service import MemberService
from ....main import get_db

router = APIRouter()

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_member(
    name: str,
    contact: str,
    level: str,
    effective_date: Optional[datetime] = None,
    custom_fields: Optional[dict] = None,
    db: Session = Depends(get_db)
):
    """
    Create a new member with encrypted sensitive data
    """
    member_service = MemberService(db)
    
    # Encrypt sensitive fields in custom_fields if provided
    if custom_fields:
        encrypted_fields = {}
        for key, value in custom_fields.items():
            if is_sensitive_field(key):
                encrypted_fields[key] = encrypt_sensitive_data(value)
            else:
                encrypted_fields[key] = value
        custom_fields = encrypted_fields
    
    member = member_service.create_member(
        name=name,
        contact=contact,
        level=level,
        effective_date=effective_date,
        custom_fields=custom_fields
    )
    
    return {
        "id": member.id,
        "name": member.name,
        "contact": member.contact,
        "level": member.level,
        "effective_date": member.effective_date,
        "expiry_date": member.expiry_date,
        "custom_fields": member.custom_fields,
        "created_at": member.created_at,
        "updated_at": member.updated_at
    }

@router.get("/{member_id}", response_model=dict)
def get_member(
    member_id: int,
    db: Session = Depends(get_db)
):
    """
    Get member details with decrypted sensitive data
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # Decrypt sensitive fields in custom_fields if present
    decrypted_fields = {}
    if member.custom_fields:
        for key, value in member.custom_fields.items():
            if is_sensitive_field(key):
                decrypted_fields[key] = decrypt_sensitive_data(value)
            else:
                decrypted_fields[key] = value
    
    return {
        "id": member.id,
        "name": member.name,
        "contact": member.contact,
        "level": member.level,
        "effective_date": member.effective_date,
        "expiry_date": member.expiry_date,
        "custom_fields": decrypted_fields,
        "created_at": member.created_at,
        "updated_at": member.updated_at
    }

@router.put("/{member_id}/level", response_model=dict)
def update_member_level(
    member_id: int,
    new_level: str,
    db: Session = Depends(get_db)
):
    """
    Update member's level and recalculate expiry date
    """
    member_service = MemberService(db)
    updated_member = member_service.update_member_level(member_id, new_level)
    
    if not updated_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    return {
        "id": updated_member.id,
        "name": updated_member.name,
        "contact": updated_member.contact,
        "level": updated_member.level,
        "effective_date": updated_member.effective_date,
        "expiry_date": updated_member.expiry_date,
        "custom_fields": updated_member.custom_fields,
        "created_at": updated_member.created_at,
        "updated_at": updated_member.updated_at
    }

@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    member_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a member
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    db.delete(member)
    db.commit()
    
    return None

@router.get("/", response_model=List[dict])
def list_members(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    level: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    List members with optional filtering by level
    """
    query = db.query(Member)
    
    if level:
        query = query.filter(Member.level == level)
    
    members = query.offset(skip).limit(limit).all()
    
    result = []
    for member in members:
        # Decrypt sensitive fields in custom_fields if present
        decrypted_fields = {}
        if member.custom_fields:
            for key, value in member.custom_fields.items():
                if is_sensitive_field(key):
                    decrypted_fields[key] = decrypt_sensitive_data(value)
                else:
                    decrypted_fields[key] = value
        
        result.append({
            "id": member.id,
            "name": member.name,
            "contact": member.contact,
            "level": member.level,
            "effective_date": member.effective_date,
            "expiry_date": member.expiry_date,
            "custom_fields": decrypted_fields,
            "created_at": member.created_at,
            "updated_at": member.updated_at
        })
    
    return result
