from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, check_permission, Permission
from app.models.user import User
from app.models.membership import Membership
from app.models.plan import Plan
from app.schemas.membership import MembershipResponse, RenewalRequest
from app.services.membership_service import MembershipService
from app.core.observability import tracer, logger

router = APIRouter(prefix="/membership", tags=["membership"])
membership_service = MembershipService()

@router.get("/status", response_model=MembershipResponse)
@tracer.start_as_current_span("get_membership_status")
async def get_membership_status(
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permission(Permission.VIEW_MEMBERSHIP))
):
    """Get current membership status"""
    try:
        logger.info(f"Getting membership status for user {current_user.id}")
        return await membership_service.get_membership_status(current_user.id)
    except Exception as e:
        logger.error(f"Failed to get membership status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve membership status"
        )

@router.post("/renew")
@tracer.start_as_current_span("renew_membership")
async def renew_membership(
    renewal_request: RenewalRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permission(Permission.RENEW_MEMBERSHIP))
):
    """Renew membership with selected plan"""
    try:
        logger.info(f"User {current_user.id} renewing membership with plan {renewal_request.plan_id}")
        result = await membership_service.renew_membership(
            user_id=current_user.id,
            plan_id=renewal_request.plan_id,
            payment_method=renewal_request.payment_method
        )
        return {
            "success": True,
            "message": "Membership renewed successfully",
            "payment_id": result.get("payment_id"),
            "new_end_date": result.get("new_end_date")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to renew membership: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to renew membership"
        )

@router.get("/plans")
@tracer.start_as_current_span("get_available_plans")
async def get_available_plans(
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permission(Permission.VIEW_MEMBERSHIP))
):
    """Get list of available membership plans"""
    try:
        with get_db() as db:
            plans = db.query(Plan).filter(Plan.is_active == True).all()
            return [
                {
                    "id": plan.id,
                    "name": plan.name,
                    "duration_months": plan.duration_months,
                    "price": plan.price,
                    "features": plan.features
                }
                for plan in plans
            ]
    except Exception as e:
        logger.error(f"Failed to get available plans: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available plans"
        )

@router.post("/auto-renew")
@tracer.start_as_current_span("toggle_auto_renew")
async def toggle_auto_renew(
    enabled: bool,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permission(Permission.RENEW_MEMBERSHIP))
):
    """Toggle auto-renewal for membership"""
    try:
        with get_db() as db:
            membership = db.query(Membership).filter(
                Membership.user_id == current_user.id
            ).first()
            
            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Membership not found"
                )
            
            membership.auto_renew = enabled
            db.commit()
            
            # Clear cache
            cache_key = f"membership_status:{current_user.id}"
            membership_service.redis_client.delete(cache_key)
            
            return {
                "success": True,
                "message": f"Auto-renewal {'enabled' if enabled else 'disabled'} successfully"
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle auto-renew: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update auto-renewal settings"
        )
