from datetime import date
from typing import Optional
from enum import Enum
from pydantic import Field
from datetime import datetime
from typing import List

from pydantic import BaseModel


class MemberStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"
    EXPIRED = "expired"
    DELETED = "deleted"
    ARCHIVED = "archived"
    TRIAL = "trial"
    VIP = "vip"
    FROZEN = "frozen"
    GRADUATED = "graduated"


class MemberBase(BaseModel):
    name: str
    phone: str
    join_date: date
    membership_type: str
    preferred_language: str = "en"
    timezone: str = "UTC"
    status: MemberStatus = MemberStatus.ACTIVE
    is_deleted: bool = Field(default=False, description="Soft delete flag")
    deleted_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when member was soft deleted"
    )
    deleted_by: Optional[int] = Field(
        default=None,
        description="ID of admin who performed soft delete"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Custom tags for member categorization"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes about the member"
    )
    emergency_contact: Optional[str] = Field(
        default=None,
        description="Emergency contact information"
    )
    last_active_at: Optional[datetime] = Field(
        default=None,
        description="Last active timestamp"
    )
    status_changed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when status was last changed"
    )
    status_changed_by: Optional[int] = Field(
        default=None,
        description="ID of admin who changed the status"
    )


class MemberCreate(MemberBase):
    pass


class MemberUpdate(BaseModel):
    name: Optional[str] = Field(
        default=None,
        description="Updated member name"
    )
    phone: Optional[str] = Field(
        default=None,
        description="Updated phone number"
    )
    membership_type: Optional[str] = Field(
        default=None,
        description="Updated membership type"
    )
    preferred_language: Optional[str] = Field(
        default=None,
        description="Updated preferred language"
    )
    timezone: Optional[str] = Field(
        default=None,
        description="Updated timezone"
    )
    status: Optional[MemberStatus] = Field(
        default=None,
        description="Updated member status"
    )
    is_deleted: Optional[bool] = Field(
        default=None,
        description="Soft delete status"
    )
    deleted_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp for soft delete"
    )
    deleted_by: Optional[int] = Field(
        default=None,
        description="ID of admin who performed soft delete"
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Updated tags list"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Updated notes"
    )
    emergency_contact: Optional[str] = Field(
        default=None,
        description="Updated emergency contact"
    )
    last_active_at: Optional[datetime] = Field(
        default=None,
        description="Updated last active timestamp"
    )
    status_changed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when status was last changed"
    )
    status_changed_by: Optional[int] = Field(
        default=None,
        description="ID of admin who changed the status"
    )


class Member(MemberBase):
    id: int

    class Config:
        orm_mode = True