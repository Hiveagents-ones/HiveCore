from celery import Celery
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.member import Member
from app.models.membership_plan import MembershipPlan
from app.models.payment import Payment
from app.services.payment_gateway import PaymentGatewayService

# Initialize Celery
celery_app = Celery(
    "member_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)


def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def update_membership_status(self, payment_id: int) -> dict:
    """
    Update membership status after successful payment with transaction handling
    
    Args:
        payment_id: ID of the payment record
        
    Returns:
        dict: Result of the operation
    """
    db = next(get_db())
    
    try:
        # Start transaction
        with db.begin():
            # Get payment record
            payment = db.query(Payment).filter(Payment.id == payment_id).first()
            if not payment:
                raise ValueError(f"Payment with id {payment_id} not found")
            
            # Verify payment status
            if payment.status != "completed":
                raise ValueError(f"Payment {payment_id} is not completed")
            
            # Get member
            member = db.query(Member).filter(Member.id == payment.member_id).first()
            if not member:
                raise ValueError(f"Member with id {payment.member_id} not found")
            
            # Get membership plan
            plan = db.query(MembershipPlan).filter(MembershipPlan.id == payment.plan_id).first()
            if not plan:
                raise ValueError(f"Membership plan with id {payment.plan_id} not found")
            
            # Calculate new expiry date
            if member.expiry_date and member.expiry_date > datetime.utcnow():
                # Extend from current expiry date
                new_expiry = member.expiry_date + timedelta(days=plan.duration_days)
            else:
                # Set from today
                new_expiry = datetime.utcnow() + timedelta(days=plan.duration_days)
            
            # Update member status
            member.expiry_date = new_expiry
            member.status = "active"
            member.plan_id = plan.id
            
            # Update payment record
            payment.processed_at = datetime.utcnow()
            payment.status = "processed"
            
            # Commit transaction
            db.commit()
            
            # Refresh objects to get updated values
            db.refresh(member)
            db.refresh(payment)
            
            return {
                "success": True,
                "member_id": member.id,
                "new_expiry_date": member.expiry_date.isoformat(),
                "payment_id": payment.id,
                "plan_name": plan.name
            }
            
    except Exception as exc:
        # Rollback transaction automatically on exception
        db.rollback()
        
        # Retry logic
        if self.request.retries < self.max_retries:
            # Exponential backoff
            countdown = 2 ** self.request.retries * 60
            raise self.retry(exc=exc, countdown=countdown)
        
        # Log error and return failure
        return {
            "success": False,
            "error": str(exc),
            "payment_id": payment_id,
            "retries": self.request.retries
        }
    
    finally:
        db.close()


@celery_app.task
def check_expired_memberships() -> dict:
    """
    Check and update expired memberships (scheduled task)
    
    Returns:
        dict: Summary of expired memberships updated
    """
    db = next(get_db())
    
    try:
        with db.begin():
            # Find expired active members
            expired_members = db.query(Member).filter(
                Member.status == "active",
                Member.expiry_date < datetime.utcnow()
            ).all()
            
            updated_count = 0
            for member in expired_members:
                member.status = "expired"
                updated_count += 1
            
            db.commit()
            
            return {
                "success": True,
                "updated_count": updated_count,
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as exc:
        db.rollback()
        return {
            "success": False,
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def process_refund(self, payment_id: int, reason: str) -> dict:
    """
    Process refund and update membership status with transaction handling
    
    Args:
        payment_id: ID of the payment to refund
        reason: Reason for refund
        
    Returns:
        dict: Result of the refund operation
    """
    db = next(get_db())
    
    try:
        with db.begin():
            # Get payment record
            payment = db.query(Payment).filter(Payment.id == payment_id).first()
            if not payment:
                raise ValueError(f"Payment with id {payment_id} not found")
            
            # Check if already refunded
            if payment.status == "refunded":
                raise ValueError(f"Payment {payment_id} is already refunded")
            
            # Process refund through payment gateway
            payment_service = PaymentGatewayService()
            refund_result = payment_service.process_refund(
                payment.transaction_id,
                payment.amount,
                reason
            )
            
            if not refund_result["success"]:
                raise ValueError(f"Refund failed: {refund_result.get('error', 'Unknown error')}")
            
            # Get member
            member = db.query(Member).filter(Member.id == payment.member_id).first()
            if not member:
                raise ValueError(f"Member with id {payment.member_id} not found")
            
            # Update payment status
            payment.status = "refunded"
            payment.refunded_at = datetime.utcnow()
            payment.refund_reason = reason
            payment.refund_transaction_id = refund_result["refund_id"]
            
            # Revert membership status if this was the last payment
            recent_payments = db.query(Payment).filter(
                Payment.member_id == member.id,
                Payment.status == "completed",
                Payment.created_at > payment.created_at
            ).count()
            
            if recent_payments == 0:
                # This was the last payment, revert membership
                member.status = "inactive"
                member.expiry_date = None
                member.plan_id = None
            
            db.commit()
            
            return {
                "success": True,
                "payment_id": payment_id,
                "refund_id": refund_result["refund_id"],
                "member_status_updated": recent_payments == 0
            }
            
    except Exception as exc:
        db.rollback()
        
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries * 60
            raise self.retry(exc=exc, countdown=countdown)
        
        return {
            "success": False,
            "error": str(exc),
            "payment_id": payment_id,
            "retries": self.request.retries
        }
    
    finally:
        db.close()


# Schedule periodic tasks
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'check-expired-memberships': {
        'task': 'app.tasks.check_expired_memberships',
        'schedule': crontab(hour=0, minute=0),  # Run daily at midnight UTC
    },
}