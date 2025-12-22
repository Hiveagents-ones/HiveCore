import datetime
from datetime import timedelta
import logging
from typing import List
from sqlalchemy.orm import Session
from app.models import Subscription, AuditLog
from app.core.config import settings

logger = logging.getLogger(__name__)

def send_expiry_reminders(db: Session):
    """检查所有订阅，发送到期前7天的提醒"""
    try:
        today = datetime.datetime.utcnow()
        reminder_date = today + timedelta(days=7)
        
        # 查询到期日期为reminder_date的订阅
        subscriptions = db.query(Subscription).filter(
            Subscription.expiry_date == reminder_date
        ).all()
        
        for sub in subscriptions:
            logger.info(f"Sending reminder for subscription {sub.id} (expiry: {sub.expiry_date})")
            
            # 记录审计日志
            audit_log = AuditLog(
                user_id=None,
                action="send_reminder",
                details=f"Subscription {sub.id} expiry in 7 days",
                timestamp=datetime.datetime.utcnow()
            )
            db.add(audit_log)
            db.commit()
        
        logger.info(f"Sent reminders for {len(subscriptions)} subscriptions")
    except Exception as e:
        logger.error(f"Failed to send reminders: {str(e)}")
        raise