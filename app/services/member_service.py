"""Member service layer.

This module contains business logic for member management operations.
All database operations use async/await pattern with SQLAlchemy.
"""

import datetime
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound

from app.models.member import Member, RenewalRecord
from app.schemas.member import MemberCreate, MemberUpdate, RenewalRequest


class MemberNotFoundError(Exception):
    """Exception raised when a member is not found."""

    def __init__(self, identifier: str) -> None:
        """Initialize exception.

        Args:
            identifier: The ID or phone number that was not found
        """
        self.identifier = identifier
        super().__init__(f"Member not found: {identifier}")


class MemberService:
    """Service for member-related operations.

    This class provides methods for querying, creating, and updating members,
    as well as handling membership renewals.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def get_member(self, id_or_phone: int | str) -> Member:
        """Get member by ID or phone number.

        Args:
            id_or_phone: Member ID (int) or phone number (str)

        Returns:
            Member: The member instance

        Raises:
            MemberNotFoundError: If member is not found
        """
        if isinstance(id_or_phone, int):
            stmt = select(Member).where(Member.id == id_or_phone)
        else:
            # Validate phone format
            if not id_or_phone.isdigit():
                raise ValueError("Phone number must contain only digits")
            stmt = select(Member).where(Member.phone == id_or_phone)

        try:
            result = await self.db.execute(stmt)
            member = result.scalar_one()
        except NoResultFound as e:
            raise MemberNotFoundError(str(id_or_phone)) from e

        return member

    async def get_member_by_id(self, member_id: int) -> Member:
        """Get member by ID.

        Args:
            member_id: Member ID

        Returns:
            Member: The member instance

        Raises:
            MemberNotFoundError: If member is not found
        """
        return await self.get_member(member_id)

    async def get_member_by_phone(self, phone: str) -> Member:
        """Get member by phone number.

        Args:
            phone: Member phone number

        Returns:
            Member: The member instance

        Raises:
            MemberNotFoundError: If member is not found
        """
        return await self.get_member(phone)

    async def get_member_by_phone_optional(self, phone: str) -> Optional[Member]:
        """Get member by phone number, returning None if not found.

        Args:
            phone: Member phone number

        Returns:
            Member | None: The member instance or None
        """
        stmt = select(Member).where(Member.phone == phone)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_member(self, data: MemberCreate) -> Member:
        """Create a new member.

        Args:
            data: Member creation data

        Returns:
            Member: The created member instance

        Raises:
            ValueError: If phone number already exists
        """
        # Check if phone already exists
        existing = await self.get_member_by_phone_optional(data.phone)
        if existing:
            raise ValueError(f"Member with phone {data.phone} already exists")

        member = Member(
            phone=data.phone,
            name=data.name,
            validity_start=data.validity_start,
            validity_end=data.validity_end,
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def update_member(
        self, member_id: int, data: MemberUpdate
    ) -> Member:
        """Update member information.

        Args:
            member_id: Member ID
            data: Member update data

        Returns:
            Member: The updated member instance

        Raises:
            MemberNotFoundError: If member is not found
        """
        member = await self.get_member_by_id(member_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(member, field, value)

        member.updated_at = datetime.datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def update_member_validity(
        self,
        member_id: int,
        validity_end: datetime.datetime,
    ) -> Member:
        """Update member validity period.

        Args:
            member_id: Member ID
            validity_end: New validity end date

        Returns:
            Member: The updated member instance

        Raises:
            MemberNotFoundError: If member is not found
            ValueError: If validity_end is in the past
        """
        member = await self.get_member_by_id(member_id)

        if validity_end < datetime.datetime.utcnow():
            raise ValueError("Validity end date cannot be in the past")

        member.validity_end = validity_end
        member.updated_at = datetime.datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def verify_member_exists(self, member_id: int) -> bool:
        """Verify if a member exists.

        Args:
            member_id: Member ID

        Returns:
            bool: True if member exists, False otherwise
        """
        stmt = select(func.count(Member.id)).where(Member.id == member_id)
        result = await self.db.execute(stmt)
        count = result.scalar()
        return count > 0

    async def is_member_expired(self, member_id: int) -> bool:
        """Check if member's validity has expired.

        Args:
            member_id: Member ID

        Returns:
            bool: True if expired, False otherwise

        Raises:
            MemberNotFoundError: If member is not found
        """
        member = await self.get_member_by_id(member_id)
        return member.is_expired

    async def renew_membership(
        self,
        member_id: int,
        request: RenewalRequest,
        payment_verified: bool = False,
    ) -> tuple[Member, RenewalRecord]:
        """Renew member membership.

        Args:
            member_id: Member ID
            request: Renewal request data
            payment_verified: Whether payment has been verified

        Returns:
            tuple: (updated_member, renewal_record)

        Raises:
            MemberNotFoundError: If member is not found
            ValueError: If payment is not verified or other validation errors
        """
        member = await self.get_member_by_id(member_id)

        # Validate payment status if payment_id is provided
        if request.payment_id and not payment_verified:
            raise ValueError("Payment not verified. Please verify payment before renewal.")

        # Calculate new validity end date
        previous_end = member.validity_end
        now = datetime.datetime.utcnow()

        # If already expired, start from today; otherwise extend from current end date
        base_date = max(previous_end, now)
        new_end = base_date + datetime.timedelta(days=request.days)

        # Create renewal record
        renewal_record = RenewalRecord(
            member_id=member.id,
            previous_end=previous_end,
            new_end=new_end,
            days_added=request.days,
            payment_status="completed" if payment_verified else "pending",
            amount=request.amount,
        )
        self.db.add(renewal_record)

        # Update member validity
        member.validity_end = new_end
        member.updated_at = now

        await self.db.commit()
        await self.db.refresh(member)
        await self.db.refresh(renewal_record)

        return member, renewal_record

    async def create_renewal_record(
        self,
        member_id: int,
        previous_end: datetime.datetime,
        new_end: datetime.datetime,
        days_added: int,
        payment_status: str = "pending",
        amount: Optional[float] = None,
    ) -> RenewalRecord:
        """Create a renewal record.

        Args:
            member_id: Member ID
            previous_end: Previous validity end date
            new_end: New validity end date
            days_added: Number of days added
            payment_status: Payment transaction status
            amount: Renewal amount

        Returns:
            RenewalRecord: The created renewal record
        """
        renewal_record = RenewalRecord(
            member_id=member_id,
            previous_end=previous_end,
            new_end=new_end,
            days_added=days_added,
            payment_status=payment_status,
            amount=amount,
        )
        self.db.add(renewal_record)
        await self.db.commit()
        await self.db.refresh(renewal_record)
        return renewal_record

    async def get_renewal_records(
        self,
        member_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RenewalRecord]:
        """Get renewal records.

        Args:
            member_id: Optional member ID to filter records
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            list[RenewalRecord]: List of renewal records
        """
        stmt = select(RenewalRecord)
        if member_id is not None:
            stmt = stmt.where(RenewalRecord.member_id == member_id)
        stmt = stmt.order_by(RenewalRecord.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_members(
        self,
        active_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Member]:
        """List members with optional filtering.

        Args:
            active_only: Only return active (non-expired) members
            limit: Maximum number of members to return
            offset: Number of members to skip

        Returns:
            list[Member]: List of members
        """
        stmt = select(Member).order_by(Member.created_at.desc()).limit(limit).offset(offset)

        if active_only:
            now = datetime.datetime.utcnow()
            stmt = stmt.where(
                and_(
                    Member.validity_start <= now,
                    Member.validity_end >= now,
                )
            )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_member(self, member_id: int) -> None:
        """Delete a member.

        Args:
            member_id: Member ID

        Raises:
            MemberNotFoundError: If member is not found
        """
        member = await self.get_member_by_id(member_id)
        await self.db.delete(member)
        await self.db.commit()
