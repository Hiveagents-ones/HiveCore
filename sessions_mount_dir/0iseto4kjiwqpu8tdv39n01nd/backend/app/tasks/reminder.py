from datetime import datetime, timedelta
from typing import List

from celery import Celery
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.subscription import Subscription, SubscriptionStatus
from app.core.config import settings

# Initialize Celery
celery_app = Celery(
    "reminder",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "check-expiring-subscriptions": {
            "task": "app.tasks.reminder.check_expiring_subscriptions",
            "schedule": 60.0,  # Run every minute
        },
        "check-expired-subscriptions": {
            "task": "app.tasks.reminder.check_expired_subscriptions",
            "schedule": 3600.0,  # Run every hour
        },
    },
)


@celery_app.task
def check_expiring_subscriptions():
    """
    Check for subscriptions that will expire in the next 7 days
    and send reminder notifications.
    """
    db: Session = next(get_db())
    try:
        # Get subscriptions expiring in the next 7 days
        seven_days_from_now = datetime.utcnow() + timedelta(days=7)
        expiring_subscriptions = db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.end_date <= seven_days_from_now,
            Subscription.end_date > datetime.utcnow(),
            Subscription.auto_renew == False
        ).all()

        for subscription in expiring_subscriptions:
            # Send reminder notification (implementation depends on notification system)
            send_reminder_notification.delay(
                user_id=str(subscription.user_id),
                subscription_id=subscription.id,
                days_remaining=subscription.days_remaining(),
                plan_name=subscription.plan.name
            )

        return {
            "status": "success",
            "count": len(expiring_subscriptions),
            "message": f"Processed {len(expiring_subscriptions)} expiring subscriptions"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    finally:
        db.close()


@celery_app.task
def check_expired_subscriptions():
    """
    Check for subscriptions that have expired and update their status.
    """
    db: Session = next(get_db())
    try:
        # Get subscriptions that have expired
        expired_subscriptions = db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.end_date <= datetime.utcnow()
        ).all()

        for subscription in expired_subscriptions:
            # Update subscription status to expired
            subscription.status = SubscriptionStatus.EXPIRED
            db.commit()

            # Send expiration notification
            send_expiration_notification.delay(
                user_id=str(subscription.user_id),
                subscription_id=subscription.id,
                plan_name=subscription.plan.name
            )

        return {
            "status": "success",
            "count": len(expired_subscriptions),
            "message": f"Processed {len(expired_subscriptions)} expired subscriptions"
        }
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": str(e)
        }
    finally:
        db.close()


@celery_app.task
def send_reminder_notification(user_id: str, subscription_id: int, days_remaining: int, plan_name: str):
    """
    Send reminder notification to user about expiring subscription.
    This is a placeholder - actual implementation depends on notification system.
    """
    # TODO: Implement actual notification sending logic
    # This could integrate with email service, push notifications, etc.
    print(f"Reminder sent to user {user_id}: Subscription {subscription_id} ({plan_name}) expires in {days_remaining} days")
    return {
        "status": "success",
        "message": "Reminder notification sent"
    }


@celery_app.task
def send_expiration_notification(user_id: str, subscription_id: int, plan_name: str):
    """
    Send expiration notification to user about expired subscription.
    This is a placeholder - actual implementation depends on notification system.
    """
    # TODO: Implement actual notification sending logic
    # This could integrate with email service, push notifications, etc.
    print(f"Expiration notice sent to user {user_id}: Subscription {subscription_id} ({plan_name}) has expired")
    return {
        "status": "success",
        "message": "Expiration notification sent"
    }


@celery_app.task
def send_renewal_success_notification(user_id: str, subscription_id: int, plan_name: str):
    """
    Send notification to user about successful subscription renewal.
    This is a placeholder - actual implementation depends on notification system.
    """
    # TODO: Implement actual notification sending logic
    print(f"Renewal success sent to user {user_id}: Subscription {subscription_id} ({plan_name}) renewed successfully")
    return {
        "status": "success",
        "message": "Renewal success notification sent"
    }


@celery_app.task
def send_payment_failed_notification(user_id: str, subscription_id: int, plan_name: str):
    """
    Send notification to user about failed payment for subscription renewal.
    This is a placeholder - actual implementation depends on notification system.
    """
    # TODO: Implement actual notification sending logic
    print(f"Payment failure sent to user {user_id}: Subscription {subscription_id} ({plan_name}) payment failed")
    return {
        "status": "success",
        "message": "Payment failure notification sent"
    }
