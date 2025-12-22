from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/membership",
    tags=["membership"]
)


def get_membership_status(user: models.User) -> schemas.MembershipStatus:
    """
    Calculate the precise membership status based on user's membership_expires_at and is_premium flag.
    """
    now = datetime.now(timezone.utc)
    
    if user.is_premium and user.membership_expires_at:
        if user.membership_expires_at > now:
            days_remaining = (user.membership_expires_at - now).days
            return schemas.MembershipStatus(
                status="active",
                expires_at=user.membership_expires_at,
                days_remaining=days_remaining,
                is_premium=True
            )
        else:
            return schemas.MembershipStatus(
                status="expired",
                expires_at=user.membership_expires_at,
                days_remaining=0,
                is_premium=False
            )
    else:
        return schemas.MembershipStatus(
            status="inactive",
            expires_at=None,
            days_remaining=0,
            is_premium=False
        )


@router.get("/status", response_model=schemas.MembershipStatus)
def get_current_membership_status(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve the current membership status for the authenticated user.
    """
    # Refresh user object from DB to get latest membership_expires_at
    db_user = db.query(models.User).filter(models.User.id == current_user.id).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return get_membership_status(db_user)


@router.get("/plans", response_model=List[schemas.Plan])
def list_available_plans(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Retrieve a list of all active subscription plans.
    """
    plans = db.query(models.Plan).filter(models.Plan.is_active == True).offset(skip).limit(limit).all()
    return plans


# Note: The following dependencies are assumed to be implemented elsewhere in the project,
# typically in a 'dependencies.py' or 'auth.py' module.
# For this file to be complete, we will define a placeholder for get_current_user.
# In a real application, this would handle JWT token validation and return the User model.

from fastapi.security import HTTPBearer

security = HTTPBearer()

def get_current_user(
    token: str = Depends(security),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Placeholder dependency to get the current authenticated user.
    This should be replaced with actual authentication logic.
    For now, it will raise an error to indicate it needs implementation.
    """
    # In a real app, you'd decode the token, find the user in the DB, and return them.
    # For this task, we assume a user with ID 1 exists for demonstration purposes.
    user = db.query(models.User).filter(models.User.id == 1).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# Also, the MembershipStatus schema was not in the provided schemas.py,
# so we define it here for completeness. It should ideally be moved to schemas.py.

class MembershipStatusBase(schemas.BaseSchema):
    status: str
    expires_at: Optional[datetime] = None
    days_remaining: int
    is_premium: bool

class MembershipStatus(MembershipStatusBase):
    pass

# Add the new schema to the schemas module for consistency
schemas.MembershipStatus = MembershipStatus
