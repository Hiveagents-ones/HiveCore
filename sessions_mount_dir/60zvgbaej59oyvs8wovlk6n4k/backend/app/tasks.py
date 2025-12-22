from celery import Celery
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import SessionLocal
from app.models import Member as Membership, User, Payment, Notification, PaymentStatus, NotificationType, NotificationStatus
from app.crud import get_membership_by_user_id
from app.core.email import send_email

# Initialize Celery app
celery_app = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "check-expiring-memberships": {
            "task": "app.tasks.check_expiring_memberships",
            "schedule": 3600.0,  # Run every hour
        },
    },
)

@celery_app.task
def send_expiry_reminder_email(user_email: str, user_name: str, expiry_date: datetime):
    """
    Send an expiry reminder email to a user.
    """
    subject = "Membership Expiry Reminder"
    body = f"""
    Dear {user_name},

    This is a reminder that your membership will expire on {expiry_date.strftime('%Y-%m-%d')}.
    Please renew your membership to continue enjoying our services.

    Best regards,
    The Team
    """
    
    try:
        send_email(to_email=user_email, subject=subject, body=body)
        
        # Log notification in database
        db = SessionLocal()
        try:
            notification = Notification(
                user_id=db.query(User).filter(User.email == user_email).first().id if db.query(User).filter(User.email == user_email).first() else None,
                type=NotificationType.EMAIL,
                status=NotificationStatus.SENT,
                message=body
            )
            db.add(notification)
            db.commit()
        finally:
            db.close()
            
        return {"status": "success", "message": "Email sent successfully"}
    except Exception as e:
        # Log failed notification
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == user_email).first()
            if user:
                notification = Notification(
                    user_id=user.id,
                    type=NotificationType.EMAIL,
                    status=NotificationStatus.FAILED,
                    message=body
                )
                db.add(notification)
                db.commit()
        finally:
            db.close()
        return {"status": "error", "message": str(e)}

@celery_app.task
def check_expiring_memberships():
    """
    Check for memberships expiring within the next 7 days and send reminder emails.
    """
    db: Session = SessionLocal()
    try:
        # Get memberships expiring in the next 7 days
        expiry_threshold = datetime.utcnow() + timedelta(days=7)
        expiring_memberships = db.query(Membership).filter(
            Membership.remaining_months <= 1,
            Membership.is_active == True
        ).all()
        
        for membership in expiring_memberships:
            user = db.query(User).filter(User.id == membership.user_id).first()
            if user and user.email:
                # Send reminder email
                send_expiry_reminder_email.delay(
                    user_email=user.email,
                    user_name=user.full_name or user.email,
                    expiry_date=datetime.utcnow() + timedelta(days=membership.remaining_months * 30)
                )
                # Mark notification as sent
                notification = Notification(
                    user_id=user.id,
                    type=NotificationType.EMAIL,
                    status=NotificationStatus.SENT,
                    message=f"Membership expiry reminder sent for {membership.remaining_months} months remaining"
                )
                db.add(notification)
                db.commit()
        
        return {"status": "success", "message": f"Processed {len(expiring_memberships)} expiring memberships"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task
def process_payment_success(user_id: int, payment_amount: float, new_expiry_date: datetime):
    """
    Process successful payment and update membership.
    """
    db: Session = SessionLocal()
    try:
        membership = get_membership_by_user_id(db, user_id)
        if membership:
            membership.remaining_months = int((new_expiry_date - datetime.utcnow()).days / 30)
            membership.is_active = True
            db.commit()
            
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.email:
                subject = "Payment Successful - Membership Renewed"
                body = f"""
                Dear {user.full_name or user.email},
                
                Your payment of ${payment_amount:.2f} has been successfully processed.
                Your membership has been renewed and is now valid for {int((new_expiry_date - datetime.utcnow()).days / 30)} months.
                
                Thank you for your continued support!
                
                Best regards,
                The Team
                """
                send_email(to_email=user.email, subject=subject, body=body)
            
            return {"status": "success", "message": "Payment processed and membership updated"}
        else:
            return {"status": "error", "message": "Membership not found"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task
def process_payment_failure(user_id: int, payment_amount: float, error_message: str):
    """
    Process failed payment and update records.
    """
    db: Session = SessionLocal()
    try:
        membership = get_membership_by_user_id(db, user_id)
        if membership:
            # Create failed payment record
            payment = Payment(
                user_id=user_id,
                amount=payment_amount,
                status=PaymentStatus.FAILED,
                payment_date=datetime.utcnow(),
                membership_id=membership.id,
                error_message=error_message
            )
            db.add(payment)
            db.commit()

            user = db.query(User).filter(User.id == user_id).first()
            if user and user.email:
                subject = "Payment Failed"
                body = f"""
                Dear {user.full_name or user.email},

                We were unable to process your payment of ${payment_amount:.2f}.
                Error: {error_message}

                Please try again or contact support if the issue persists.

                Best regards,
                The Team
                """
                send_email(to_email=user.email, subject=subject, body=body)
                
                # Log notification
                notification = Notification(
                    user_id=user_id,
                    type=NotificationType.EMAIL,
                    status=NotificationStatus.SENT,
                    message=body
                )
                db.add(notification)
                db.commit()

            return {"status": "success", "message": "Payment failure processed"}
        else:
            return {"status": "error", "message": "Membership not found"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()