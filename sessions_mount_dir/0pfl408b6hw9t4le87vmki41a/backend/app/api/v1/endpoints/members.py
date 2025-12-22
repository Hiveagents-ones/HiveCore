from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.crud import member as crud_member
from app.schemas import member as schemas_member

router = APIRouter()


@router.post("/", response_model=schemas_member.Member)
def create_member(
    *,
    db: Session = Depends(deps.get_db),
    member_in: schemas_member.MemberCreate
):
    """
    Create new member.
    """
    member = crud_member.member.get_by_phone(db, phone=member_in.phone)
    if member:
        raise HTTPException(
            status_code=400,
            detail="The member with this phone number already exists in the system.",
        )
    member = crud_member.member.create(db, obj_in=member_in)
    return member


@router.get("/", response_model=schemas_member.MemberList)
def read_members(
    db: Session = Depends(deps.get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
):
    """
    Retrieve members.
    """
    if search:
        members = crud_member.member.search_members(db, query=search, skip=skip, limit=limit)
        total = len(crud_member.member.search_members(db, query=search))
    elif is_active is not None:
        if is_active:
            members = crud_member.member.get_active_members(db)
        else:
            members = crud_member.member.get_expired_members(db)
        total = len(members)
        members = members[skip : skip + limit]
    else:
        members = crud_member.member.get_multi(db, skip=skip, limit=limit)
        total = len(crud_member.member.get_multi(db))
    
    pages = (total + limit - 1) // limit
    page = skip // limit + 1
    
    return {
        "members": members,
        "total": total,
        "page": page,
        "per_page": limit,
        "pages": pages,
    }


@router.get("/{member_id}", response_model=schemas_member.Member)
def read_member(
    *,
    db: Session = Depends(deps.get_db),
    member_id: int
):
    """
    Get member by ID.
    """
    member = crud_member.member.get(db, id=member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@router.put("/{member_id}", response_model=schemas_member.Member)
def update_member(
    *,
    db: Session = Depends(deps.get_db),
    member_id: int,
    member_in: schemas_member.MemberUpdate
):
    """
    Update a member.
    """
    member = crud_member.member.get(db, id=member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    member = crud_member.member.update(db, db_obj=member, obj_in=member_in)
    return member


@router.delete("/{member_id}", response_model=schemas_member.Member)
def delete_member(
    *,
    db: Session = Depends(deps.get_db),
    member_id: int
):
    """
    Delete a member.
    """
    member = crud_member.member.get(db, id=member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    member = crud_member.member.remove(db, id=member_id)
    return member
