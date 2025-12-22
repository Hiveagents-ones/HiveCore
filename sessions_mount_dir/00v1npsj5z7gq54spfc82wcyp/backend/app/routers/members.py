from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Member
from ..schemas import MemberCreate, MemberUpdate, MemberResponse
from ..utils import get_current_user
from fastapi import status
from fastapi import Request
from fastapi import Header
from ..monitoring import PrometheusMiddleware
from ..monitoring import MEMBER_OPERATIONS, MEMBER_LATENCY, ACTIVE_MEMBERS, MEMBER_TYPE_COUNTER, MEMBER_AGE_GAUGE, MEMBER_ACTIVITY_COUNTER, MEMBER_LAST_ACTIVITY
from ..i18n import gettext as _

router = APIRouter(
    prefix="/members",
    tags=["members"],
    route_class=PrometheusMiddleware
)

@router.get("/metrics", include_in_schema=False)
@router.get("/metrics/activity", include_in_schema=False)
async def get_member_activity_metrics():
    """Get member activity related metrics"""
    return {
        "activity_count": {
            str(k): v for k, v in MEMBER_ACTIVITY_COUNTER._metrics.items()
        },
        "last_activity": {
            str(k): v._value.get() for k, v in MEMBER_LAST_ACTIVITY._metrics.items()
        }
    }
async def get_member_metrics():
    """Get member related metrics"""
    return {
        "active_members": ACTIVE_MEMBERS._value.get(),
        "operations": {
            "create": MEMBER_OPERATIONS.labels('create', 'success')._value.get(),
            "get": MEMBER_OPERATIONS.labels('get', 'success')._value.get(),
            "update": MEMBER_OPERATIONS.labels('update', 'success')._value.get(),
            "delete": MEMBER_OPERATIONS.labels('delete', 'success')._value.get()
        }
    }
@router.get("/", response_model=List[MemberResponse], status_code=status.HTTP_200_OK)
def get_members(
    accept_language: str = Header(None, description="Language preference"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
    request: Request
):
    """Get all members list"""
    with MEMBER_LATENCY.labels('list').time():
        MEMBER_OPERATIONS.labels('list', 'started').inc()
        try:
            members = db.query(Member).offset(skip).limit(limit).all()
            ACTIVE_MEMBERS.set(len(members))
            # Track member activity
            for m in members:
                MEMBER_ACTIVITY_COUNTER.labels(str(m.id), 'view').inc()
                MEMBER_LAST_ACTIVITY.labels(str(m.id)).set_to_current_time()
            MEMBER_OPERATIONS.labels('list', 'success').inc()
            return members
        except Exception as e:
            MEMBER_OPERATIONS.labels('list', 'failed').inc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=_("Failed to retrieve members")
            )

@router.post("/", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def create_member(
    accept_language: str = Header(None, description="Language preference"),
    member: MemberCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
    request: Request
):
    """Create new member"""
    with MEMBER_LATENCY.labels('create').time():
        MEMBER_OPERATIONS.labels('create', 'started').inc()
        try:
            member_data = member.dict()
            db_member = Member(**member_data)
            db.add(db_member)
            db.commit()
            db.refresh(db_member)
            ACTIVE_MEMBERS.inc()
            MEMBER_OPERATIONS.labels('create', 'success').inc()
            # Track member demographics and activity
            member_data = {
                'id': str(db_member.id),
                'membership_type': getattr(db_member, 'membership_type', 'unknown'),
                'age': getattr(db_member, 'age', 0)
            }
            MEMBER_ACTIVITY_COUNTER.labels(str(db_member.id), 'create').inc()
            MEMBER_LAST_ACTIVITY.labels(str(db_member.id)).set_to_current_time()
            if hasattr(db_member, 'membership_type'):
                MEMBER_TYPE_COUNTER.labels(db_member.membership_type).inc()
            if hasattr(db_member, 'age'):
                age_group = f"{(db_member.age // 10) * 10}-{(db_member.age // 10) * 10 + 9}"
                MEMBER_AGE_GAUGE.labels(age_group).inc()
            return db_member
        except Exception as e:
            MEMBER_OPERATIONS.labels('create', 'failed').inc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=_("Failed to create member")
            )

@router.get("/{member_id}", response_model=MemberResponse, status_code=status.HTTP_200_OK)
def get_member(
    accept_language: str = Header(None, description="Language preference"),
    member_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
    request: Request
):
    """Get member by ID"""
    with MEMBER_LATENCY.labels('get').time():
        MEMBER_OPERATIONS.labels('get', 'started').inc()
        try:
            member = db.query(Member).filter(Member.id == member_id).first()
            if member is None:
                MEMBER_OPERATIONS.labels('get', 'failed').inc()
                raise HTTPException(status_code=404, detail=_("Member not found"))
            MEMBER_OPERATIONS.labels('get', 'success').inc()
            # Track member activity
            MEMBER_ACTIVITY_COUNTER.labels(str(member.id), 'view').inc()
            MEMBER_LAST_ACTIVITY.labels(str(member.id)).set_to_current_time()
            return member
        except Exception as e:
            MEMBER_OPERATIONS.labels('get', 'failed').inc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=_("Failed to retrieve member")
            )

@router.put("/{member_id}", response_model=MemberResponse, status_code=status.HTTP_200_OK)
def update_member(
    accept_language: str = Header(None, description="Language preference"),
    member_id: int,
    member: MemberUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
    request: Request
):
    """Update member information"""
    with MEMBER_LATENCY.labels('update').time():
        MEMBER_OPERATIONS.labels('update', 'started').inc()
        try:
            db_member = db.query(Member).filter(Member.id == member_id).first()
            if db_member is None:
                MEMBER_OPERATIONS.labels('update', 'failed').inc()
                raise HTTPException(status_code=404, detail=_("Member not found"))
        except Exception as e:
            MEMBER_OPERATIONS.labels('update', 'failed').inc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=_("Failed to update member")
            )
    
    update_data = member.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_member, key, value)
    
    try:
        db.add(db_member)
        db.commit()
        db.refresh(db_member)
        MEMBER_OPERATIONS.labels('update', 'success').inc()
        # Track member activity
        MEMBER_ACTIVITY_COUNTER.labels(str(db_member.id), 'update').inc()
        MEMBER_LAST_ACTIVITY.labels(str(db_member.id)).set_to_current_time()
        return db_member
    except Exception as e:
        db.rollback()
        MEMBER_OPERATIONS.labels('update', 'failed').inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_("Failed to update member")
        )

@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    accept_language: str = Header(None, description="Language preference"),
    member_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
    request: Request
):
    """Delete member"""
    with MEMBER_LATENCY.labels('delete').time():
        MEMBER_OPERATIONS.labels('delete', 'started').inc()
        try:
            member = db.query(Member).filter(Member.id == member_id).first()
            if member is None:
                MEMBER_OPERATIONS.labels('delete', 'failed').inc()
                raise HTTPException(status_code=404, detail=_("Member not found"))
        except Exception as e:
            MEMBER_OPERATIONS.labels('delete', 'failed').inc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=_("Failed to delete member")
            )
    
    try:
        db.delete(member)
        db.commit()
        ACTIVE_MEMBERS.dec()
        MEMBER_OPERATIONS.labels('delete', 'success').inc()
        # Track member activity
        MEMBER_ACTIVITY_COUNTER.labels(str(member.id), 'delete').inc()
        MEMBER_LAST_ACTIVITY.labels(str(member.id)).set_to_current_time()
        return None
    except Exception as e:
        db.rollback()
        MEMBER_OPERATIONS.labels('delete', 'failed').inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_("Failed to delete member")
        )