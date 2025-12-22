from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.reminder_service import update_reminder_config
from pydantic import BaseModel


class ReminderConfigUpdate(BaseModel):
    days_before_expiry: int


doc = """Update renewal reminder configuration"""

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.put("/config", summary="Update reminder configuration", description=doc)
async def update_reminder_config_endpoint(
    config: ReminderConfigUpdate,
    db: Session = Depends(get_db)
):
    """Update the number of days before expiry to send reminders"""
    try:
        update_reminder_config(db, config.days_before_expiry)
        return {
            "message": "Reminder configuration updated successfully",
            "days_before_expiry": config.days_before_expiry
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update reminder configuration: {str(e)}"
        )