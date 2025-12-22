import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.reminder_service import ReminderService

logger = logging.getLogger(__name__)


class MembershipScheduler:
    """Scheduler for membership-related tasks."""

    def __init__(self):
        self.db: Optional[Session] = None
        self.reminder_service: Optional[ReminderService] = None
        self.is_running = False

    async def start(self) -> None:
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        self.is_running = True
        logger.info("Starting membership scheduler")

        try:
            while self.is_running:
                try:
                    # Create new database session for each iteration
                    self.db = SessionLocal()
                    self.reminder_service = ReminderService(self.db)

                    # Check membership expiry
                    await self.reminder_service.check_membership_expiry()

                    # Sleep for 24 hours before next check
                    await asyncio.sleep(86400)  # 24 hours in seconds

                except SQLAlchemyError as e:
                    logger.error(f"Database error in scheduler: {e}")
                    await asyncio.sleep(3600)  # Wait 1 hour before retry
                except Exception as e:
                    logger.error(f"Unexpected error in scheduler: {e}")
                    await asyncio.sleep(3600)  # Wait 1 hour before retry
                finally:
                    if self.db:
                        self.db.close()
                        self.db = None
                        self.reminder_service = None

        except asyncio.CancelledError:
            logger.info("Scheduler cancelled")
        finally:
            self.is_running = False
            logger.info("Membership scheduler stopped")

    def stop(self) -> None:
        """Stop the scheduler."""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return

        self.is_running = False
        logger.info("Stopping membership scheduler")


# Global scheduler instance
scheduler = MembershipScheduler()


async def run_scheduler() -> None:
    """Run the membership scheduler."""
    await scheduler.start()


def stop_scheduler() -> None:
    """Stop the membership scheduler."""
    scheduler.stop()
