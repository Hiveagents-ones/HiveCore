from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..models.coach import Coach, CoachLeave
from ..schemas.coach import CoachWorkingHours
from ..database import get_db

router = APIRouter(
    prefix="/api/v1/coaches",
    tags=["coaches"]
)


@router.get("/", response_model=List[Coach])
def get_coaches(db: Session = Depends(get_db)):
    """获取所有教练列表"""
    return db.query(Coach).all()


@router.post("/", response_model=Coach, status_code=status.HTTP_201_CREATED)
def create_coach(coach: Coach, db: Session = Depends(get_db)):
    """创建新教练"""
    db.add(coach)
    db.commit()
    db.refresh(coach)
    return coach


@router.get("/{coach_id}", response_model=Coach)
def get_coach(coach_id: int, db: Session = Depends(get_db)):
    """获取单个教练信息"""
    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    return coach


@router.put("/{coach_id}", response_model=Coach)
def update_coach(coach_id: int, coach_data: dict, db: Session = Depends(get_db)):
    """更新教练信息"""
    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    
    for key, value in coach_data.items():
        setattr(coach, key, value)
    
    db.commit()
    db.refresh(coach)
    return coach


@router.delete("/{coach_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_coach(coach_id: int, db: Session = Depends(get_db)):
    """删除教练"""
    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    
    db.delete(coach)
    db.commit()


# 教练排班管理相关API
@router.put("/{coach_id}/schedule", response_model=Coach)
@router.put("/{coach_id}/working-hours", response_model=Coach)
def set_coach_working_hours(coach_id: int, working_hours: CoachWorkingHours, db: Session = Depends(get_db)):
    """设置教练工作时间"""
    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    
    coach.working_hours = working_hours.working_hours
    coach.available_days = working_hours.available_days
    coach.max_courses_per_day = working_hours.max_courses_per_day
    
    db.commit()
    db.refresh(coach)
    return coach
def update_coach_schedule(coach_id: int, schedule: dict, db: Session = Depends(get_db)):
    """更新教练工作时间安排"""
    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    
    coach.work_schedule = schedule
    db.commit()
    db.refresh(coach)
    return coach


@router.post("/{coach_id}/leaves", response_model=CoachLeave, status_code=status.HTTP_201_CREATED)
def create_coach_leave(coach_id: int, leave: CoachLeave, db: Session = Depends(get_db)):
    """创建教练请假申请"""
    leave.coach_id = coach_id
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return leave


@router.get("/{coach_id}/leaves", response_model=List[CoachLeave])
def get_coach_leaves(coach_id: int, db: Session = Depends(get_db)):
    """获取教练请假记录"""
    return db.query(CoachLeave).filter(CoachLeave.coach_id == coach_id).all()