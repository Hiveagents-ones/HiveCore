from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ..database import get_db
from ..models import Coach, Schedule
from ..schemas import CoachCreate, CoachResponse, ScheduleCreate, ScheduleResponse

router = APIRouter(
    prefix="/api/v1/coaches",
    tags=["coaches"]
)

@router.get("/", response_model=List[CoachResponse])
def get_coaches(db: Session = Depends(get_db)):
    """获取所有教练列表"""
    return db.query(Coach).all()

@router.post("/", response_model=CoachResponse)
def create_coach(coach: CoachCreate, db: Session = Depends(get_db)):
    """创建新教练"""
    db_coach = Coach(**coach.dict())
    db.add(db_coach)
    db.commit()
    db.refresh(db_coach)
    return db_coach

@router.put("/{coach_id}", response_model=CoachResponse)
def update_coach(coach_id: int, coach: CoachCreate, db: Session = Depends(get_db)):
    """更新教练信息"""
    db_coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not db_coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    
    for key, value in coach.dict().items():
        setattr(db_coach, key, value)
    
    db.commit()
    db.refresh(db_coach)
    return db_coach

@router.get("/schedules", response_model=List[ScheduleResponse])
@router.get("/schedules/{coach_id}", response_model=List[ScheduleResponse])
def get_coach_schedules_by_id(coach_id: int, db: Session = Depends(get_db)):
    """获取指定教练的排班信息"""
    return db.query(Schedule).filter(Schedule.coach_id == coach_id).all()
def get_coach_schedules(db: Session = Depends(get_db)):
    """获取所有教练排班信息"""
    return db.query(Schedule).all()

@router.post("/schedules", response_model=ScheduleResponse)
@router.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
@router.delete("/schedules/{schedule_id}")
def delete_coach_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """删除教练排班"""
    db_schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    db.delete(db_schedule)
    db.commit()
    return {"message": "Schedule deleted successfully"}
def update_coach_schedule(schedule_id: int, schedule: ScheduleCreate, db: Session = Depends(get_db)):
    """更新教练排班"""
    db_schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # 检查时间冲突（排除当前排班）
    conflicting_schedules = db.query(Schedule).filter(
        Schedule.coach_id == schedule.coach_id,
        Schedule.id != schedule_id,
        Schedule.start_time < schedule.end_time,
        Schedule.end_time > schedule.start_time
    ).all()

    if conflicting_schedules:
        raise HTTPException(status_code=400, detail="Schedule conflict detected")

    for key, value in schedule.dict().items():
        setattr(db_schedule, key, value)

    db.commit()
    db.refresh(db_schedule)
    return db_schedule
def create_coach_schedule(schedule: ScheduleCreate, db: Session = Depends(get_db)):
    """创建教练排班"""
    # 检查时间冲突
    conflicting_schedules = db.query(Schedule).filter(
        Schedule.coach_id == schedule.coach_id,
        Schedule.start_time < schedule.end_time,
        Schedule.end_time > schedule.start_time
    ).all()
    
    if conflicting_schedules:
        raise HTTPException(status_code=400, detail="Schedule conflict detected")
    
    db_schedule = Schedule(**schedule.dict())
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule