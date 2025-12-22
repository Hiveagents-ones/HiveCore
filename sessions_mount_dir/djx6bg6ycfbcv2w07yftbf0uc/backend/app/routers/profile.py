from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional
import shutil
import os
from datetime import datetime

from .. import models, schemas
from ..database import get_db
from ..utils import get_current_user

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.get("/profile", response_model=schemas.User)
def get_profile(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's profile"""
    return current_user

@router.put("/profile", response_model=schemas.User)
def update_profile(
    profile_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile"""
    update_data = profile_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/profile/avatar", response_model=schemas.User)
def upload_avatar(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload user avatar"""
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Create uploads directory if it doesn't exist
    upload_dir = "uploads/avatars"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    file_extension = file.filename.split(".")[-1]
    filename = f"{current_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}"
    file_path = os.path.join(upload_dir, filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Update user avatar URL
    current_user.avatar_url = f"/{file_path}"
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.get("/profile/public/{user_id}", response_model=schemas.UserPublic)
def get_public_profile(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get public profile of a user"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check privacy settings
    if user.privacy_settings:
        if user.privacy_settings.profile_visibility == "private":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This profile is private"
            )
    
    return user

@router.get("/profile/privacy", response_model=schemas.PrivacySettings)
def get_privacy_settings(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's privacy settings"""
    if not current_user.privacy_settings:
        # Create default privacy settings if they don't exist
        privacy_settings = models.PrivacySettings(user_id=current_user.id)
        db.add(privacy_settings)
        db.commit()
        db.refresh(privacy_settings)
        return privacy_settings
    
    return current_user.privacy_settings

@router.put("/profile/privacy", response_model=schemas.PrivacySettings)
def update_privacy_settings(
    privacy_update: schemas.PrivacySettingsUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's privacy settings"""
    if not current_user.privacy_settings:
        # Create privacy settings if they don't exist
        privacy_settings = models.PrivacySettings(user_id=current_user.id)
        db.add(privacy_settings)
        db.commit()
        db.refresh(privacy_settings)
    else:
        privacy_settings = current_user.privacy_settings
    
    update_data = privacy_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(privacy_settings, field, value)
    
    privacy_settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(privacy_settings)
    return privacy_settings
