import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.models.member import Member
from app.models.payment import Payment
from app.utils.email import send_email
from app.utils.redis import redis_client

logger = logging.getLogger(__name__)


class ReminderService:
    def __init__(self, db: Session):
        self.db = db
        self.retry_limit = 3
        self.retry_delay = 5  # seconds

    async def check_membership_expiry(self) -> None:
        """Check for memberships expiring soon and send reminders."""
        try:
            # Get members whose membership expires in the next 30 days
            expiry_threshold = datetime.utcnow() + timedelta(days=30)
            expiring_members = (
                self.db.query(Member)
                .filter(
                    Member.membership_end <= expiry_threshold,
                    Member.membership_end > datetime.utcnow(),
                    Member.is_active == True,
                )
                .all()
            )

            for member in expiring_members:
                await self._send_reminder_with_retry(member)

        except SQLAlchemyError as e:
            logger.error(f"Database error while checking membership expiry: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in check_membership_expiry: {e}")
            raise

    async def _send_reminder_with_retry(self, member: Member) -> None:
        """Send reminder with retry mechanism."""
        retry_count = 0
        last_error = None

        while retry_count < self.retry_limit:
            try:
                # Check if reminder already sent
                cache_key = f"reminder:{member.id}:{member.membership_end}"
                if await redis_client.get(cache_key):
                    logger.info(f"Reminder already sent for member {member.id}")
                    return

                # Send email reminder
                await self._send_expiry_email(member)

                # Mark reminder as sent in cache
                await redis_client.setex(
                    cache_key,
                    timedelta(days=7),  # Cache for 7 days
                    "sent"
                )

                logger.info(f"Successfully sent reminder to member {member.id}")
                return

            except Exception as e:
                last_error = e
                retry_count += 1
                logger.warning(
                    f"Attempt {retry_count} failed for member {member.id}: {e}"
                )
                if retry_count < self.retry_limit:
                    await asyncio.sleep(self.retry_delay)

        logger.error(
            f"Failed to send reminder to member {member.id} after {self.retry_limit} attempts. "
            f"Last error: {last_error}"
        )

    async def _send_expiry_email(self, member: Member) -> None:
        """Send expiry notification email."""
        try:
            days_until_expiry = (member.membership_end - datetime.utcnow()).days
            subject = "Membership Expiry Reminder"

            if days_until_expiry <= 7:
                urgency = "URGENT: "
                message = (
                    f"Dear {member.name},\n\n"
                    f"Your membership will expire in {days_until_expiry} days "
                    f"on {member.membership_end.strftime('%Y-%m-%d')}.\n\n"
                    f"Please renew your membership to continue enjoying our services.\n\n"
                    f"You can renew online or visit our facility.\n\n"
                    f"Best regards,\n"
                    f"The Membership Team"
                )
            else:
                urgency = ""
                message = (
                    f"Dear {member.name},\n\n"
                    f"This is a friendly reminder that your membership will expire "
                    f"in {days_until_expiry} days on {member.membership_end.strftime('%Y-%m-%d')}.\n\n"
                    f"Plan ahead and renew your membership to avoid any interruption in service.\n\n"
                    f"Best regards,\n"
                    f"The Membership Team"
                )

            await send_email(
                to_email=member.email,
                subject=f"{urgency}{subject}",
                body=message
            )

        except Exception as e:
            logger.error(f"Failed to send email to member {member.id}: {e}")
            raise

    async def get_payment_history(self, member_id: int) -> List[Payment]:
        """Get payment history for a member."""
        try:
            payments = (
                self.db.query(Payment)
                .filter(Payment.member_id == member_id)
                .order_by(Payment.payment_date.desc())
                .all()
            )
            return payments

        except SQLAlchemyError as e:
            logger.error(f"Database error while fetching payment history: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_payment_history: {e}")
            raise

    async def record_payment(
        self,
        member_id: int,
        amount: float,
        payment_method: str,
        payment_date: Optional[datetime] = None,
        transaction_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Payment:
        """Record a new payment for a member."""
        try:
            if payment_date is None:
                payment_date = datetime.utcnow()

            payment = Payment(
                member_id=member_id,
                amount=amount,
                payment_method=payment_method,
                payment_date=payment_date,
                transaction_id=transaction_id,
                notes=notes,
                status="completed"
            )

            self.db.add(payment)
            self.db.commit()
            self.db.refresh(payment)

            # Update member's membership end date if applicable
            member = self.db.query(Member).filter(Member.id == member_id).first()
            if member and member.membership_end:
                # Extend membership by 1 year for standard payments
                member.membership_end = member.membership_end + timedelta(days=365)
                self.db.commit()

            logger.info(f"Recorded payment {payment.id} for member {member_id}")
            return payment

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error while recording payment: {e}")
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error in record_payment: {e}")
            raise

    async def send_payment_confirmation(self, payment: Payment) -> None:
        """Send payment confirmation email."""
        try:
            member = self.db.query(Member).filter(Member.id == payment.member_id).first()
            if not member:
                logger.error(f"Member not found for payment {payment.id}")
                return

            subject = "Payment Confirmation"
            message = (
                f"Dear {member.name},\n\n"
                f"We have received your payment of ${payment.amount:.2f} "
                f"via {payment.payment_method}.\n\n"
                f"Payment Date: {payment.payment_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Transaction ID: {payment.transaction_id or 'N/A'}\n\n"
                f"Your membership has been extended. "
                f"New expiry date: {member.membership_end.strftime('%Y-%m-%d')}\n\n"
                f"Thank you for your continued support!\n\n"
                f"Best regards,\n"
                f"The Membership Team"
            )

            await send_email(
                to_email=member.email,
                subject=subject,
                body=message
            )

            logger.info(f"Sent payment confirmation for payment {payment.id}")

        except Exception as e:
            logger.error(f"Failed to send payment confirmation: {e}")
            raise
