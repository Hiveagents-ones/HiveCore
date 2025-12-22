from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.membership import MembershipPlan
from app.schemas.membership import MembershipPlanResponse

router = APIRouter(prefix="/membership", tags=["membership"])

@router.get("/plans", response_model=List[MembershipPlanResponse])
def get_membership_plans(db: Session = Depends(get_db)):
    """
    获取所有可用的会员套餐信息
    """
    try:
        plans = db.query(MembershipPlan).filter(MembershipPlan.is_active == True).all()
        return plans
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch membership plans")

@router.get("/plans/{plan_id}", response_model=MembershipPlanResponse)
def get_membership_plan(plan_id: int, db: Session = Depends(get_db)):
    """
    根据ID获取特定会员套餐信息
    """
    plan = db.query(MembershipPlan).filter(
        MembershipPlan.id == plan_id,
        MembershipPlan.is_active == True
    ).first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Membership plan not found")
    
    return plan