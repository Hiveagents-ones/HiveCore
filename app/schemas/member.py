"""Pydantic schemas for member management.

This module contains request/response schemas for member-related operations.
"""

import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MemberBase(BaseModel):
    """Base member schema with common fields."""

    phone: str = Field(..., min_length=10, max_length=20, description="Member phone number")
    name: str = Field(..., min_length=1, max_length=100, description="Member name")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone number format.

        Args:
            v: Phone number string

        Returns:
            str: Validated phone number

        Raises:
            ValueError: If phone number contains invalid characters
        """
        if not v.isdigit():
            raise ValueError("Phone number must contain only digits")
        return v


class MemberCreate(MemberBase):
    """Schema for creating a new member."""

    validity_start: Optional[datetime.datetime] = Field(
        default_factory=datetime.datetime.utcnow,
        description="Membership validity start date"
    )
    validity_end: datetime.datetime = Field(..., description="Membership validity end date")


class MemberUpdate(BaseModel):
    """Schema for updating member information."""

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Member name")
    validity_end: Optional[datetime.datetime] = Field(
        None, description="Membership validity end date"
    )


class MemberResponse(MemberBase):
    """Schema for member response."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Member ID")
    validity_start: datetime.datetime = Field(..., description="Membership validity start date")
    validity_end: datetime.datetime = Field(..., description="Membership validity end date")
    is_active: bool = Field(..., description="Whether membership is currently valid")
    is_expired: bool = Field(..., description="Whether membership has expired")
    created_at: datetime.datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime.datetime = Field(..., description="Record update timestamp")


class RenewalRequest(BaseModel):
    """Schema for membership renewal request."""

    days: int = Field(..., gt=0, le=3650, description="Number of days to add (max 10 years)")
    amount: Optional[float] = Field(None, gt=0, description="Renewal amount")
    payment_id: Optional[str] = Field(None, description="Payment transaction ID")


class RenewalResponse(BaseModel):
    """Schema for renewal response."""

    member_id: int = Field(..., description="Member ID")
    previous_end: datetime.datetime = Field(..., description="Previous validity end date")
    new_end: datetime.datetime = Field(..., description="New validity end date")
    days_added: int = Field(..., description="Number of days added")
    payment_status: str = Field(..., description="Payment transaction status")
    amount: Optional[float] = Field(None, description="Renewal amount")


class RenewalRecordResponse(BaseModel):
    """Schema for renewal record response."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Record ID")
    member_id: int = Field(..., description="Member ID")
    previous_end: datetime.datetime = Field(..., description="Previous validity end date")
    new_end: datetime.datetime = Field(..., description="New validity end date")
    days_added: int = Field(..., description="Number of days added")
    payment_status: str = Field(..., description="Payment transaction status")
    amount: Optional[float] = Field(None, description="Renewal amount")
    created_at: datetime.datetime = Field(..., description="Record creation timestamp")


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    code: Optional[str] = Field(None, description="Error code")


class MessageResponse(BaseModel):
    """Schema for generic message responses."""

    message: str = Field(..., description="Response message")
