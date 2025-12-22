from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..models.coach import Coach, CoachLeave
from ..database import get_db

router = APIRouter(
    prefix="/api/v1/coaches",
    tags=["approvals"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{coach_id}/leaves", response_model=List[dict])
async def get_coach_leaves(
    coach_id: int,
    status_filter: str = None,
    db: Session = Depends(get_db)
):
    """获取教练的请假记录"""
    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not coach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coach not found"
        )

    query = db.query(CoachLeave).filter(CoachLeave.coach_id == coach_id)
    if status_filter:
        query = query.filter(CoachLeave.status == status_filter)

    leaves = query.all()
    return [
        {
            "id": leave.id,
            "start_date": leave.start_date,
            "end_date": leave.end_date,
            "reason": leave.reason,
            "status": leave.status
        }
        for leave in leaves
    ]


@router.post("/{coach_id}/leaves", status_code=status.HTTP_201_CREATED)
async def create_leave_request(
    coach_id: int,
    start_date: datetime,
    end_date: datetime,
    reason: str = None,
    db: Session = Depends(get_db)
):
    """创建请假申请"""
    if start_date >= end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date"
        )

    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not coach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coach not found"
        )

    new_leave = CoachLeave(
        coach_id=coach_id,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        status="pending"
    )

    db.add(new_leave)
    db.commit()
    db.refresh(new_leave)

    return {
        "id": new_leave.id,
        "status": "created"
    }


@router.put("/leaves/{leave_id}/approve")
async def approve_leave(
    leave_id: int,
    db: Session = Depends(get_db)
):
    """批准请假申请"""
    leave = db.query(CoachLeave).filter(CoachLeave.id == leave_id).first()
    if not leave:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave request not found"
        )

    if leave.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Leave request is not in pending status"
        )

    leave.status = "approved"
    db.commit()

    return {"status": "approved"}


@router.put("/leaves/{leave_id}/reject")
async def reject_leave(
    leave_id: int,
    db: Session = Depends(get_db)
):
    """拒绝请假申请"""
    leave = db.query(CoachLeave).filter(CoachLeave.id == leave_id).first()
    if not leave:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave request not found"
        )

    if leave.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Leave request is not in pending status"
        )

    leave.status = "rejected"
    db.commit()

    return {"status": "rejected"}