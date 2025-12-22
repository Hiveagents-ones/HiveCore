from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import redis
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.membership import Membership
from app.models.user import User
from app.models.plan import Plan
from app.core.config import settings
from app.core.database import get_db
from app.core.cache import cache_client
from app.core.tcc import tcc_transaction
from app.core.lock import distributed_lock
from app.services.payment_service import PaymentService
from app.schemas.membership import MembershipStatus, MembershipResponse

class MembershipService:
    def __init__(self):
        self.redis_client = cache_client
        self.payment_service = PaymentService()
        self.cache_ttl = 3600  # 1 hour

    async def get_membership_status(self, user_id: int) -> MembershipResponse:
        """Get current membership status with caching"""
        cache_key = f"membership_status:{user_id}"
        
        # Try to get from cache first
        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            return MembershipResponse.parse_raw(cached_data)
        
        # Get from database
        with get_db() as db:
            membership = db.query(Membership).filter(Membership.user_id == user_id).first()
            if not membership:
                raise HTTPException(status_code=404, detail="Membership not found")
            
            response = MembershipResponse(
                user_id=user_id,
                plan_id=membership.plan_id,
                status=membership.status,
                start_date=membership.start_date,
                end_date=membership.end_date,
                auto_renew=membership.auto_renew
            )
            
            # Cache the result
            self.redis_client.setex(cache_key, self.cache_ttl, response.json())
            return response

    @tcc_transaction
    async def renew_membership(self, user_id: int, plan_id: int, payment_method: str) -> Dict[str, Any]:
        """Renew membership with TCC transaction and concurrency control"""
        lock_key = f"membership_renew:{user_id}"
        
        async with distributed_lock(lock_key, timeout=30):
            # Try phase
            try_result = await self._try_renewal(user_id, plan_id, payment_method)
            if not try_result["success"]:
                raise HTTPException(status_code=400, detail=try_result["message"])
            
            # Confirm phase
            confirm_result = await self._confirm_renewal(user_id, plan_id, try_result["payment_id"])
            if not confirm_result["success"]:
                # Cancel phase
                await self._cancel_renewal(user_id, try_result["payment_id"])
                raise HTTPException(status_code=500, detail="Renewal confirmation failed")
            
            # Clear cache
            cache_key = f"membership_status:{user_id}"
            self.redis_client.delete(cache_key)
            
            return {
                "success": True,
                "message": "Membership renewed successfully",
                "new_end_date": confirm_result["new_end_date"],
                "payment_id": try_result["payment_id"]
            }

    async def _try_renewal(self, user_id: int, plan_id: int, payment_method: str) -> Dict[str, Any]:
        """Try phase of TCC transaction"""
        with get_db() as db:
            # Check user exists
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "message": "User not found"}
            
            # Check plan exists
            plan = db.query(Plan).filter(Plan.id == plan_id).first()
            if not plan:
                return {"success": False, "message": "Plan not found"}
            
            # Check current membership
            membership = db.query(Membership).filter(Membership.user_id == user_id).first()
            if not membership:
                return {"success": False, "message": "No active membership found"}
            
            # Try to create payment
            payment_result = await self.payment_service.create_payment(
                user_id=user_id,
                amount=plan.price,
                payment_method=payment_method,
                description=f"Membership renewal - {plan.name}"
            )
            
            if not payment_result["success"]:
                return {"success": False, "message": "Payment creation failed"}
            
            return {
                "success": True,
                "payment_id": payment_result["payment_id"],
                "plan_duration": plan.duration_days
            }

    async def _confirm_renewal(self, user_id: int, plan_id: int, payment_id: str) -> Dict[str, Any]:
        """Confirm phase of TCC transaction"""
        with get_db() as db:
            # Confirm payment
            payment_confirm = await self.payment_service.confirm_payment(payment_id)
            if not payment_confirm["success"]:
                return {"success": False, "message": "Payment confirmation failed"}
            
            # Get plan details
            plan = db.query(Plan).filter(Plan.id == plan_id).first()
            if not plan:
                return {"success": False, "message": "Plan not found"}
            
            # Update membership
            membership = db.query(Membership).filter(Membership.user_id == user_id).first()
            if not membership:
                return {"success": False, "message": "Membership not found"}
            
            # Calculate new end date
            current_end = membership.end_date or datetime.utcnow()
            new_end_date = current_end + timedelta(days=plan.duration_days)
            
            # Update membership record
            membership.plan_id = plan_id
            membership.end_date = new_end_date
            membership.status = MembershipStatus.ACTIVE
            membership.updated_at = datetime.utcnow()
            
            db.commit()
            
            return {
                "success": True,
                "new_end_date": new_end_date.isoformat()
            }

    async def _cancel_renewal(self, user_id: int, payment_id: str) -> None:
        """Cancel phase of TCC transaction"""
        await self.payment_service.cancel_payment(payment_id)

    async def get_available_plans(self) -> Dict[str, Any]:
        """Get all available membership plans"""
        cache_key = "available_plans"
        
        # Try to get from cache first
        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            return {"plans": cached_data}
        
        # Get from database
        with get_db() as db:
            plans = db.query(Plan).filter(Plan.is_active == True).all()
            plans_data = [
                {
                    "id": plan.id,
                    "name": plan.name,
                    "price": plan.price,
                    "duration_days": plan.duration_days,
                    "features": plan.features
                }
                for plan in plans
            ]
            
            # Cache the result
            self.redis_client.setex(cache_key, self.cache_ttl, str(plans_data))
            return {"plans": plans_data}

    async def toggle_auto_renew(self, user_id: int, auto_renew: bool) -> Dict[str, Any]:
        """Toggle auto-renewal for membership"""
        lock_key = f"membership_auto_renew:{user_id}"
        
        async with distributed_lock(lock_key, timeout=10):
            with get_db() as db:
                membership = db.query(Membership).filter(Membership.user_id == user_id).first()
                if not membership:
                    raise HTTPException(status_code=404, detail="Membership not found")
                
                membership.auto_renew = auto_renew
                membership.updated_at = datetime.utcnow()
                db.commit()
                
                # Clear cache
                cache_key = f"membership_status:{user_id}"
                self.redis_client.delete(cache_key)
                
                return {
                    "success": True,
                    "message": f"Auto-renewal {'enabled' if auto_renew else 'disabled'} successfully"
                }

    async def cancel_membership(self, user_id: int) -> Dict[str, Any]:
        """Cancel membership immediately"""
        lock_key = f"membership_cancel:{user_id}"
        
        async with distributed_lock(lock_key, timeout=10):
            with get_db() as db:
                membership = db.query(Membership).filter(Membership.user_id == user_id).first()
                if not membership:
                    raise HTTPException(status_code=404, detail="Membership not found")
                
                membership.status = MembershipStatus.CANCELLED
                membership.end_date = datetime.utcnow()
                membership.auto_renew = False
                membership.updated_at = datetime.utcnow()
                db.commit()
                
                # Clear cache
                cache_key = f"membership_status:{user_id}"
                self.redis_client.delete(cache_key)
                
                return {
                    "success": True,
                    "message": "Membership cancelled successfully"
                }
