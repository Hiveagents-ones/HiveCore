from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.v1.api import get_db
from app.crud import crud_member
from app.schemas.member import Member, MemberCreate, MemberUpdate, MemberResponse
from app.models.member import MemberStatus

router = APIRouter()


@router.post("/", response_model=MemberResponse)
def create_member(
    *,
    db: Session = Depends(get_db),
    member_in: MemberCreate
):
    """
    Create a new member.
    """
    # Check if card number already exists
    member = crud_member.get_member_by_card_number(db, card_number=member_in.card_number)
    if member:
        raise HTTPException(
            status_code=400,
            detail="The member with this card number already exists in the system.",
        )
    member = crud_member.create_member(db=db, member=member_in)
    return member


@router.get("/", response_model=List[MemberResponse])
def read_members(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=0),
    status: Optional[MemberStatus] = None
):
    """
    Retrieve members.
    """
    if status:
        members = crud_member.get_members_by_status(db, status=status, skip=skip, limit=limit)
    else:
        members = crud_member.get_members(db, skip=skip, limit=limit)
    return members


@router.get("/{member_id}", response_model=MemberResponse)
def read_member(
    *,
    db: Session = Depends(get_db),
    member_id: int
):
    """
    Get a specific member by ID.
    """
    member = crud_member.get_member(db, member_id=member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@router.put("/{member_id}", response_model=MemberResponse)
def update_member(
    *,
    db: Session = Depends(get_db),
    member_id: int,
    member_in: MemberUpdate
):
    """
    Update a member.
    """
    member = crud_member.update_member(db, member_id=member_id, member=member_in)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@router.delete("/{member_id}", response_model=MemberResponse)
def delete_member(
    *,
    db: Session = Depends(get_db),
    member_id: int
):
    """
    Delete a member.
    """
    member = crud_member.delete_member(db, member_id=member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member
