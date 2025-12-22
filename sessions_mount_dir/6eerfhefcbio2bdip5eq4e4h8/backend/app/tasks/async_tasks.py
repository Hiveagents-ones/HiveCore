import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from celery import Celery
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.cache import cache_client
from app.services.payment_service import PaymentService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery(
    "membership_tasks",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
    include=["app.tasks.async_tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.PAYMENT_TIMEOUT,
    task_soft_time_limit=settings.PAYMENT_TIMEOUT - 30,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)


@celery_app.task(bind=True, max_retries=settings.QUEUE_MAX_RETRIES)
def export_payment_history(self, member_id: int, start_date: str, end_date: str) -> dict:
    """
    Async task to export payment history for a member.
    
    Args:
        member_id: ID of the member
        start_date: Start date for the export period (YYYY-MM-DD)
        end_date: End date for the export period (YYYY-MM-DD)
    
    Returns:
        dict: Task result with export status and file path
    """
    try:
        db = next(get_db())
        payment_service = PaymentService(db)
        
        # Parse dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Get payment history
        payments = payment_service.get_payment_history(member_id, start_dt, end_dt)
        
        # Generate CSV export
        filename = f"payment_history_{member_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = f"/tmp/exports/{filename}"
        
        # Create export directory if it doesn't exist
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Write CSV
        with open(filepath, 'w', newline='') as csvfile:
            import csv
            writer = csv.writer(csvfile)
            writer.writerow(['Payment ID', 'Date', 'Amount', 'Method', 'Status', 'Description'])
            
            for payment in payments:
                writer.writerow([
                    payment.id,
                    payment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    payment.amount,
                    payment.method,
                    payment.status,
                    payment.description or ''
                ])
        
        # Cache the export result
        cache_key = f"{settings.CACHE_PREFIX}export:{member_id}:{self.request.id}"
        cache_client.set(
            cache_key,
            {"status": "completed", "filepath": filepath, "filename": filename},
            ttl=settings.CACHE_TTL
        )
        
        logger.info(f"Successfully exported payment history for member {member_id}")
        return {
            "status": "completed",
            "filepath": filepath,
            "filename": filename,
            "record_count": len(payments)
        }
        
    except Exception as exc:
        logger.error(f"Failed to export payment history for member {member_id}: {str(exc)}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries * settings.NOTIFICATION_RETRY_DELAY
            raise self.retry(countdown=countdown, exc=exc)
        
        # Cache the failure
        cache_key = f"{settings.CACHE_PREFIX}export:{member_id}:{self.request.id}"
        cache_client.set(
            cache_key,
            {"status": "failed", "error": str(exc)},
            ttl=settings.CACHE_TTL
        )
        
        return {"status": "failed", "error": str(exc)}
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=settings.QUEUE_MAX_RETRIES)
def send_expiration_reminders(self, days_ahead: int = 30) -> dict:
    """
    Async task to send membership expiration reminders.
    
    Args:
        days_ahead: Number of days ahead to check for expiring memberships
    
    Returns:
        dict: Task result with reminder statistics
    """
    try:
        db = next(get_db())
        payment_service = PaymentService(db)
        
        # Calculate expiration threshold
        expiration_date = datetime.utcnow() + timedelta(days=days_ahead)
        
        # Get members with expiring memberships
        expiring_memberships = payment_service.get_expiring_memberships(expiration_date)
        
        reminder_count = 0
        failed_count = 0
        
        for membership in expiring_memberships:
            try:
                # Send reminder (this would integrate with your notification service)
                # For now, we'll just log it
                logger.info(
                    f"Sending expiration reminder to member {membership.member_id} "
                    f"for membership expiring on {membership.expiry_date}"
                )
                
                # Cache reminder status
                cache_key = f"{settings.CACHE_PREFIX}reminder:{membership.member_id}:{membership.expiry_date}"
                cache_client.set(
                    cache_key,
                    {"sent": True, "sent_at": datetime.utcnow().isoformat()},
                    ttl=settings.CACHE_TTL
                )
                
                reminder_count += 1
                
            except Exception as exc:
                logger.error(
                    f"Failed to send reminder to member {membership.member_id}: {str(exc)}"
                )
                failed_count += 1
        
        result = {
            "status": "completed",
            "total_checked": len(expiring_memberships),
            "reminders_sent": reminder_count,
            "failed": failed_count,
            "days_ahead": days_ahead
        }
        
        logger.info(
            f"Expiration reminder task completed: {reminder_count} sent, {failed_count} failed"
        )
        
        return result
        
    except Exception as exc:
        logger.error(f"Expiration reminder task failed: {str(exc)}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries * settings.NOTIFICATION_RETRY_DELAY
            raise self.retry(countdown=countdown, exc=exc)
        
        return {"status": "failed", "error": str(exc)}
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=settings.QUEUE_MAX_RETRIES)
def process_payment_webhook(self, webhook_data: dict) -> dict:
    """
    Async task to process payment webhooks.
    
    Args:
        webhook_data: Webhook payload from payment provider
    
    Returns:
        dict: Task result with processing status
    """
    try:
        db = next(get_db())
        payment_service = PaymentService(db)
        
        # Process webhook
        result = payment_service.process_webhook(webhook_data)
        
        if result["status"] == "success":
            logger.info(f"Successfully processed webhook for payment {result.get('payment_id')}")
            
            # Cache webhook processing result
            cache_key = f"{settings.CACHE_PREFIX}webhook:{webhook_data.get('id')}"
            cache_client.set(
                cache_key,
                {"processed": True, "processed_at": datetime.utcnow().isoformat()},
                ttl=settings.CACHE_TTL
            )
        else:
            logger.error(f"Failed to process webhook: {result.get('error')}")
        
        return result
        
    except Exception as exc:
        logger.error(f"Webhook processing failed: {str(exc)}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries * settings.NOTIFICATION_RETRY_DELAY
            raise self.retry(countdown=countdown, exc=exc)
        
        return {"status": "failed", "error": str(exc)}
    finally:
        db.close()


# Periodic task configuration
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'send-expiration-reminders': {
        'task': 'app.tasks.async_tasks.send_expiration_reminders',
        'schedule': crontab(hour=9, minute=0),  # Run daily at 9 AM UTC
        'args': (30,)  # Check for memberships expiring in 30 days
    },
}


# Task status helper functions
def get_task_status(task_id: str) -> Optional[dict]:
    """
    Get the status of an async task.
    
    Args:
        task_id: Celery task ID
    
    Returns:
        dict: Task status information or None if not found
    """
    try:
        result = celery_app.AsyncResult(task_id)
        
        if result.state == 'PENDING':
            return {'state': result.state, 'status': 'pending'}
        elif result.state == 'PROGRESS':
            return {'state': result.state, 'status': 'in_progress', 'info': result.info}
        elif result.state == 'SUCCESS':
            return {'state': result.state, 'status': 'completed', 'result': result.result}
        elif result.state == 'FAILURE':
            return {'state': result.state, 'status': 'failed', 'error': str(result.info)}
        else:
            return {'state': result.state, 'status': 'unknown'}
    except Exception as exc:
        logger.error(f"Failed to get task status for {task_id}: {str(exc)}")
        return None


def revoke_task(task_id: str, terminate: bool = False) -> bool:
    """
    Revoke an async task.
    
    Args:
        task_id: Celery task ID
        terminate: Whether to terminate the task if it's already running
    
    Returns:
        bool: True if task was revoked successfully
    """
    try:
        celery_app.control.revoke(task_id, terminate=terminate)
        logger.info(f"Task {task_id} revoked successfully")
        return True
    except Exception as exc:
        logger.error(f"Failed to revoke task {task_id}: {str(exc)}")
        return False
``