from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from sqlalchemy import func
from ..utils.date_utils import check_schedule_conflict

from ..models.coach import Coach, CoachLeave
from ..database import get_db

router = APIRouter(
    prefix="/api/v1/schedules",
    tags=["schedules"],
    responses={404: {"description": "Not found"}},
)


@router.get("/coach/{coach_id}", summary="获取教练排班信息")
async def get_coach_schedule(
    coach_id: int,
    db: Session = Depends(get_db)
):
    """获取指定教练的排班信息"""
    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not coach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coach not found"
        )
    
    return {
        "work_schedule": coach.work_schedule,
        "max_courses_per_day": coach.max_courses_per_day
    }


@router.put("/coach/{coach_id}", summary="更新教练排班信息")
async def update_coach_schedule(
    coach_id: int,
    work_schedule: str,
    max_courses_per_day: int,
    db: Session = Depends(get_db)
):
    """更新教练的排班信息"""
    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not coach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coach not found"
        )
    
    coach.work_schedule = work_schedule
    coach.max_courses_per_day = max_courses_per_day
    db.commit()
    
    return {"message": "Coach schedule updated successfully"}


@router.post("/leaves", summary="申请请假")
async def apply_leave(
    coach_id: int,
    start_date: datetime,
    end_date: datetime,
    reason: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """教练申请请假"""
    # 检查日期有效性
    if start_date >= end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date"
        )

    # 检查教练是否存在
    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not coach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coach not found"
        )
        
    # 检查排班冲突
    if check_schedule_conflict(db, coach_id, start_date, end_date):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Leave period conflicts with existing schedule"
        )
    
    # 创建请假记录
    leave = CoachLeave(
        coach_id=coach_id,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        status="pending"
    )
    
    db.add(leave)
    db.commit()
    db.refresh(leave)
    
    return {"message": "Leave application submitted successfully", "leave_id": leave.id}


@router.get("/leaves/{coach_id}", summary="获取教练请假记录")
async def get_coach_leaves(
    coach_id: int,
    db: Session = Depends(get_db)
):
    """获取指定教练的请假记录"""
    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not coach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coach not found"
        )
    
    return coach.leaves


@router.put("/leaves/{leave_id}", summary="审批请假申请")
async def approve_leave(
    leave_id: int,
    status: str,  # approved/rejected
    db: Session = Depends(get_db)
):
    """管理员审批请假申请"""
    leave = db.query(CoachLeave).filter(CoachLeave.id == leave_id).first()
    if not leave:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave record not found"
        )
    
    if status not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status value"
        )
    
    leave.status = status
    db.commit()
    
    return {"message": f"Leave application {status} successfully"}