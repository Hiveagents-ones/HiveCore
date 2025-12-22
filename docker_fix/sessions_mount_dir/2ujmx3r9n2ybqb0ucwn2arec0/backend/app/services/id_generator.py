import time
import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Member
from ..database import get_db


class IDGenerator:
    """
    A robust ID generation service that ensures uniqueness under high concurrency.
    
    This service uses a combination of timestamp and UUID to generate unique member IDs.
    It includes collision detection and retry mechanisms to handle edge cases.
    """
    
    def __init__(self):
        self.last_timestamp = 0
        self.sequence = 0
        
    async def generate_member_id(self, db: Optional[AsyncSession] = None) -> str:
        """
        Generate a unique member ID.
        
        Args:
            db: Optional database session. If None, creates a new session.
            
        Returns:
            str: A unique member ID in format: MEM + timestamp + sequence + uuid_suffix
            
        Raises:
            RuntimeError: If unable to generate a unique ID after multiple attempts
        """
        max_attempts = 10
        
        for attempt in range(max_attempts):
            # Get current timestamp in milliseconds
            current_timestamp = int(time.time() * 1000)
            
            # Reset sequence if timestamp changed
            if current_timestamp != self.last_timestamp:
                self.last_timestamp = current_timestamp
                self.sequence = 0
            
            # Increment sequence
            self.sequence += 1
            
            # Generate UUID suffix (first 8 characters)
            uuid_suffix = str(uuid.uuid4()).replace('-', '')[:8].upper()
            
            # Construct member ID
            member_id = f"MEM{current_timestamp}{self.sequence:04d}{uuid_suffix}"
            
            # Check for collision
            if db is None:
                async for session in get_db():
                    exists = await self._check_id_exists(session, member_id)
                    if not exists:
                        return member_id
            else:
                exists = await self._check_id_exists(db, member_id)
                if not exists:
                    return member_id
            
            # Small delay to avoid tight loop in case of collisions
            await asyncio.sleep(0.001)
        
        raise RuntimeError(f"Failed to generate unique member ID after {max_attempts} attempts")
    
    async def _check_id_exists(self, db: AsyncSession, member_id: str) -> bool:
        """
        Check if a member ID already exists in the database.
        
        Args:
            db: Database session
            member_id: Member ID to check
            
        Returns:
            bool: True if ID exists, False otherwise
        """
        result = await db.execute(
            select(Member).where(Member.id == member_id)
        )
        return result.scalar_one_or_none() is not None


# Global instance for reuse
id_generator = IDGenerator()


async def generate_unique_member_id(db: Optional[AsyncSession] = None) -> str:
    """
    Convenience function to generate a unique member ID.
    
    Args:
        db: Optional database session
        
    Returns:
        str: A unique member ID
    """
    return await id_generator.generate_member_id(db)