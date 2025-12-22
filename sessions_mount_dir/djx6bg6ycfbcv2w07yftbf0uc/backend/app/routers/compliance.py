from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from ..models import User, get_db
from ..core.security import get_current_user

router = APIRouter(prefix="/compliance", tags=["compliance"])

@router.get("/gdpr/data")
async def get_user_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    GDPR Article 15: Right of access
    Returns all personal data stored about the user
    """
    user_data = {
        "personal_info": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "phone": current_user.phone,
            "is_active": current_user.is_active,
            "is_verified": current_user.is_verified,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at
        },
        "bookings": [
            {
                "id": booking.id,
                "course_id": booking.course_id,
                "status": booking.status,
                "created_at": booking.created_at
            } for booking in current_user.bookings
        ],
        "reviews": [
            {
                "id": review.id,
                "course_id": review.course_id,
                "rating": review.rating,
                "comment": review.comment,
                "created_at": review.created_at
            } for review in current_user.reviews
        ]
    }
    return user_data

@router.delete("/gdpr/data")
async def delete_user_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    GDPR Article 17: Right to erasure ('right to be forgotten')
    Anonymizes or deletes user data
    """
    # Anonymize personal data
    current_user.username = f"deleted_user_{current_user.id}"
    current_user.email = f"deleted_{current_user.id}@deleted.com"
    current_user.hashed_password = ""
    current_user.full_name = None
    current_user.phone = None
    current_user.is_active = False
    current_user.is_verified = False
    
    # Mark as deleted
    current_user.updated_at = datetime.utcnow()
    
    db.commit()
    return {"message": "User data has been anonymized"}

@router.get("/gdpr/consent")
async def get_consent_status(
    current_user: User = Depends(get_current_user)
):
    """
    GDPR Article 7: Conditions for consent
    Returns user's consent status
    """
    return {
        "marketing_consent": current_user.is_verified,
        "data_processing_consent": True,
        "consent_date": current_user.created_at,
        "can_withdraw": True
    }

@router.post("/gdpr/consent/withdraw")
async def withdraw_consent(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    GDPR Article 7(3): Right to withdraw consent
    """
    current_user.is_verified = False
    current_user.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Consent withdrawn successfully"}

@router.get("/gdpr/portability")
async def export_user_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    GDPR Article 20: Right to data portability
    Returns user data in machine-readable format
    """
    user_data = await get_user_data(current_user, db)
    return {
        "export_date": datetime.utcnow(),
        "format": "json",
        "data": user_data
    }

@router.get("/privacy-policy")
async def get_privacy_policy():
    """
    Returns the current privacy policy
    """
    return {
        "version": "1.0",
        "last_updated": "2024-01-01",
        "policy": "This is our privacy policy...",
        "gdpr_compliant": True
    }

@router.get("/terms-of-service")
async def get_terms_of_service():
    """
    Returns the current terms of service
    """
    return {
        "version": "1.0",
        "last_updated": "2024-01-01",
        "terms": "These are our terms of service..."
    }
