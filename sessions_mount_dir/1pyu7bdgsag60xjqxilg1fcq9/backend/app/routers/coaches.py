from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..models.coach import Coach
from ..database import get_db

router = APIRouter(prefix="/api/v1/coaches", tags=["coaches"])


@router.get("/", response_model=List[dict])
def list_coaches(db: Session = Depends(get_db)):
    """获取所有教练列表"""
    coaches = db.query(Coach).all()
    return [{"id": coach.id, "name": coach.name, "schedule": coach.schedule} for coach in coaches]


@router.get("/{coach_id}", response_model=dict)
def get_coach(coach_id: int, db: Session = Depends(get_db)):
    """获取指定教练的详细信息"""
    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    return {"id": coach.id, "name": coach.name, "schedule": coach.schedule}


@router.post("/{coach_id}/schedule", response_model=dict)
def update_coach_schedule(
    coach_id: int, 
    schedule: dict, 
    db: Session = Depends(get_db)
):
    """更新教练的排班信息"""
    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    
    # 简单的冲突检测
    if not validate_schedule(schedule):
        raise HTTPException(status_code=400, detail="Invalid schedule format")
    
    coach.schedule = schedule
    db.commit()
    db.refresh(coach)
    return {"id": coach.id, "name": coach.name, "schedule": coach.schedule}


def validate_schedule(schedule: dict) -> bool:
    """验证排班数据格式"""
    required_keys = {"work_days", "shifts"}
    if not all(key in schedule for key in required_keys):
        return False
    
    if not isinstance(schedule["work_days"], list) or not isinstance(schedule["shifts"], list):
        return False
    
    return True


@router.get("/{coach_id}/conflicts", response_model=dict)
def check_schedule_conflicts(
    coach_id: int,
    start_time: str,
    end_time: str,
    date: str,
    db: Session = Depends(get_db)
):
    """检查教练排班冲突"""
    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    conflicts = []
    if coach.schedule:
        for shift in coach.schedule.get("shifts", []):
            if shift.get("date") == date:
                conflicts.append({
                    "date": shift["date"],
                    "start_time": shift["start_time"],
                    "end_time": shift["end_time"]
                })
    
    return {
        "has_conflict": len(conflicts) > 0,
        "conflicts": conflicts
    }