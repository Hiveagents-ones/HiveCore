from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.subscription import Subscription
from app.services.notification_service import send_reminder_notification

def check_and_send_reminders(db: Session):
    current_time = datetime.utcnow()
    seven_days_later = current_time + timedelta(days=7)
    
    subscriptions = db.query(Subscription).filter(
        Subscription.end_date <= seven_days_later,
        Subscription.end_date > current_time
    ).all()
    
    for sub in subscriptions:
        send_reminder_notification(sub.user_id, sub.id)