"""Member API routes.

This module contains FastAPI routes for member management operations.
"""

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.member import (
    ErrorResponse,
    MemberCreate,
    MemberResponse,
    MessageResponse,
    RenewalRecordResponse,
    RenewalRequest,
    RenewalResponse,
)
from app.services.member_service import MemberService, MemberNotFoundError

router = APIRouter(prefix="/members", tags=["members"])


async def get_member_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> MemberService:
    """Dependency to get member service instance.

    Args:
        db: Database session

    Returns:
        MemberService: Member service instance
    """
    return MemberService(db)


@router.get(
    "",
    response_model=list[MemberResponse],
    summary="List all members",
    responses={
        200: {"description": "List of members"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_members(
    active_only: Annotated[
        bool,
        Query(
            description="Filter to only include active (non-expired) members",
            example=False,
        )
    ] = False,
    limit: Annotated[int, Query(ge=1, le=1000, description="Maximum number of results")] = 100,
    offset: Annotated[int, Query(ge=0, description="Number of results to skip")] = 0,
    service: Annotated[MemberService, Depends(get_member_service)],
) -> list[MemberResponse]:
    """List all members with optional filtering.

    Args:
        active_only: Only return active members
        limit: Maximum number of results
        offset: Number of results to skip
        service: Member service (injected)

    Returns:
        list[MemberResponse]: List of member responses
    """
    members = await service.list_members(active_only=active_only, limit=limit, offset=offset)
    return [
        MemberResponse(
            id=m.id,
            phone=m.phone,
            name=m.name,
            validity_start=m.validity_start,
            validity_end=m.validity_end,
            is_active=m.is_active,
            is_expired=m.is_expired,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
        for m in members
    ]


@router.get(
    "/{id_or_phone}",
    response_model=MemberResponse,
    summary="Get member by ID or phone",
    responses={
        200: {"description": "Member found"},
        404: {"model": ErrorResponse, "description": "Member not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def get_member(
    id_or_phone: str,
    service: Annotated[MemberService, Depends(get_member_service)] = Depends(),
) -> MemberResponse:
    """Get member information by ID or phone number.

    Args:
        id_or_phone: Member ID (numeric) or phone number (digits)
        service: Member service (injected)

    Returns:
        MemberResponse: Member information

    Raises:
        HTTPException: If member not found (404) or invalid format (422)
    """
    try:
        # Try to parse as integer ID first
        try:
            member_id = int(id_or_phone)
            member = await service.get_member_by_id(member_id)
        except ValueError:
            # Not an integer, treat as phone number
            member = await service.get_member_by_phone(id_or_phone)
    except MemberNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Member not found", "detail": str(e)},
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "Invalid identifier format", "detail": str(e)},
        ) from e

    return MemberResponse(
        id=member.id,
        phone=member.phone,
        name=member.name,
        validity_start=member.validity_start,
        validity_end=member.validity_end,
        is_active=member.is_active,
        is_expired=member.is_expired,
        created_at=member.created_at,
        updated_at=member.updated_at,
    )


@router.post(
    "",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new member",
    responses={
        201: {"description": "Member created successfully"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        409: {"model": ErrorResponse, "description": "Phone number already exists"},
    },
)
async def create_member(
    data: MemberCreate,
    service: Annotated[MemberService, Depends(get_member_service)] = Depends(),
) -> MemberResponse:
    """Create a new member.

    Args:
        data: Member creation data
        service: Member service (injected)

    Returns:
        MemberResponse: Created member information

    Raises:
        HTTPException: If validation fails
    """
    try:
        member = await service.create_member(data)
    except ValueError as e:
        if "already exists" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "Conflict", "detail": str(e)},
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Bad request", "detail": str(e)},
        ) from e

    return MemberResponse(
        id=member.id,
        phone=member.phone,
        name=member.name,
        validity_start=member.validity_start,
        validity_end=member.validity_end,
        is_active=member.is_active,
        is_expired=member.is_expired,
        created_at=member.created_at,
        updated_at=member.updated_at,
    )


@router.post(
    "/{member_id}/renew",
    response_model=RenewalResponse,
    summary="Renew member membership",
    responses={
        200: {"description": "Membership renewed successfully"},
        404: {"model": ErrorResponse, "description": "Member not found"},
        400: {"model": ErrorResponse, "description": "Invalid renewal request"},
        402: {"model": ErrorResponse, "description": "Payment required"},
    },
)
async def renew_membership(
    member_id: int,
    request: RenewalRequest,
    payment_verified: Annotated[
        bool,
        Query(
            description="Whether payment has been verified",
            example=True,
        )
    ] = False,
    service: Annotated[MemberService, Depends(get_member_service)] = Depends(),
) -> RenewalResponse:
    """Renew member membership.

    This endpoint processes membership renewal. If a payment_id is provided,
    the payment_verified flag must be set to True to proceed.

    Args:
        member_id: Member ID
        request: Renewal request data
        payment_verified: Whether payment has been verified
        service: Member service (injected)

    Returns:
        RenewalResponse: Renewal information

    Raises:
        HTTPException: If member not found, payment not verified, or other errors
    """
    try:
        member, renewal = await service.renew_membership(
            member_id=member_id,
            request=request,
            payment_verified=payment_verified,
        )
    except MemberNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Member not found", "detail": str(e)},
        ) from e
    except ValueError as e:
        if "Payment not verified" in str(e):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={"error": "Payment required", "detail": str(e)},
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Bad request", "detail": str(e)},
        ) from e

    return RenewalResponse(
        member_id=member.id,
        previous_end=renewal.previous_end,
        new_end=renewal.new_end,
        days_added=renewal.days_added,
        payment_status=renewal.payment_status,
        amount=renewal.amount,
    )


@router.get(
    "/{member_id}/renewals",
    response_model=list[RenewalRecordResponse],
    summary="Get member renewal records",
    responses={
        200: {"description": "List of renewal records"},
        404: {"model": ErrorResponse, "description": "Member not found"},
    },
)
async def get_renewal_records(
    member_id: int,
    limit: Annotated[int, Query(ge=1, le=1000, description="Maximum number of results")] = 100,
    offset: Annotated[int, Query(ge=0, description="Number of results to skip")] = 0,
    service: Annotated[MemberService, Depends(get_member_service)] = Depends(),
) -> list[RenewalRecordResponse]:
    """Get renewal records for a member.

    Args:
        member_id: Member ID
        limit: Maximum number of results
        offset: Number of results to skip
        service: Member service (injected)

    Returns:
        list[RenewalRecordResponse]: List of renewal records

    Raises:
        HTTPException: If member not found
    """
    # Verify member exists
    try:
        await service.get_member_by_id(member_id)
    except MemberNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Member not found", "detail": str(e)},
        ) from e

    records = await service.get_renewal_records(member_id=member_id, limit=limit, offset=offset)

    return [
        RenewalRecordResponse(
            id=r.id,
            member_id=r.member_id,
            previous_end=r.previous_end,
            new_end=r.new_end,
            days_added=r.days_added,
            payment_status=r.payment_status,
            amount=r.amount,
            created_at=r.created_at,
        )
        for r in records
    ]


@router.delete(
    "/{member_id}",
    response_model=MessageResponse,
    summary="Delete a member",
    responses={
        200: {"description": "Member deleted successfully"},
        404: {"model": ErrorResponse, "description": "Member not found"},
    },
)
async def delete_member(
    member_id: int,
    service: Annotated[MemberService, Depends(get_member_service)] = Depends(),
) -> MessageResponse:
    """Delete a member.

    Args:
        member_id: Member ID
        service: Member service (injected)

    Returns:
        MessageResponse: Success message

    Raises:
        HTTPException: If member not found
    """
    try:
        await service.delete_member(member_id)
    except MemberNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Member not found", "detail": str(e)},
        ) from e

    return MessageResponse(message=f"Member {member_id} deleted successfully")
