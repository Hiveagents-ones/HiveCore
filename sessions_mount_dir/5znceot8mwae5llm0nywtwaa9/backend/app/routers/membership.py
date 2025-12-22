from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.membership import Membership, MembershipPlan
from app.schemas.membership import MembershipStatus, MembershipPlanResponse
from app.core.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/membership", tags=["membership"])

@router.get("/status", response_model=MembershipStatus)
async def get_membership_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's membership status"""
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.is_active == True
    ).first()
    
    if not membership:
        return MembershipStatus(
            is_member=False,
            plan_name=None,
            start_date=None,
            end_date=None,
            days_remaining=0
        )
    
    return MembershipStatus(
        is_member=True,
        plan_name=membership.plan.name,
        start_date=membership.start_date,
        end_date=membership.end_date,
        days_remaining=(membership.end_date - membership.start_date).days
    )

@router.get("/plans", response_model=List[MembershipPlanResponse])
async def get_membership_plans(
    db: Session = Depends(get_db)
):
    """Get all available membership plans"""
    plans = db.query(MembershipPlan).filter(
        MembershipPlan.is_active == True
    ).all()
    
    return [
        MembershipPlanResponse(
            id=plan.id,
            name=plan.name,
            description=plan.description,
            price=plan.price,
            duration_days=plan.duration_days,
            features=plan.features
        )
        for plan in plans
    ]

@router.post("/renew/{plan_id}")
async def renew_membership(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate membership renewal for a specific plan"""
    plan = db.query(MembershipPlan).filter(
        MembershipPlan.id == plan_id,
        MembershipPlan.is_active == True
    ).first()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership plan not found"
        )
    
    # TODO: Implement payment processing
    # This is a placeholder for payment integration
    payment_result = {
        "success": True,
        "payment_method": "placeholder",
        "transaction_id": "placeholder_id"
    }
    
    if not payment_result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment failed"
        )
    
    # Update or create membership
    existing_membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.is_active == True
    ).first()
    
    if existing_membership:
        # Extend existing membership
        existing_membership.end_date = existing_membership.end_date + \
            timedelta(days=plan.duration_days)
    else:
        # Create new membership
        new_membership = Membership(
            user_id=current_user.id,
            plan_id=plan.id,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=plan.duration_days),
            is_active=True
        )
        db.add(new_membership)
    
    db.commit()
    
    return {"message": "Membership renewed successfully"}
