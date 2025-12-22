from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Schedule, Coach
from ..schemas import ScheduleCreate, Schedule as ScheduleSchema

router = APIRouter(
    prefix="/api/v1/coaches",
    tags=["schedules"],
)

@router.get("/{coach_id}/schedule", response_model=List[ScheduleSchema])
def get_coach_schedules(coach_id: int, db: Session = Depends(get_db)):
    """获取指定教练的排班表"""
    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    
    schedules = db.query(Schedule).filter(Schedule.coach_id == coach_id).all()
    return schedules

@router.post("/{coach_id}/schedule", response_model=ScheduleSchema)
def create_coach_schedule(
    coach_id: int, 
    schedule: ScheduleCreate, 
    db: Session = Depends(get_db)
):
    """为教练创建排班"""
    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    
    # 检查时间冲突
    existing_schedule = db.query(Schedule).filter(
        Schedule.coach_id == coach_id,
        Schedule.day_of_week == schedule.day_of_week,
        Schedule.start_hour == schedule.start_hour
    ).first()
    
    if existing_schedule:
        raise HTTPException(status_code=400, detail="Schedule conflict")
    
    db_schedule = Schedule(
        coach_id=coach_id,
        day_of_week=schedule.day_of_week,
        start_hour=schedule.start_hour,
        end_hour=schedule.end_hour
    )
    
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule