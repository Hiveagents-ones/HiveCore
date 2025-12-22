from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Coach, CoachSchedule
from ..schemas import CoachCreate, CoachUpdate, CoachScheduleCreate, CoachScheduleResponse
from datetime import datetime

router = APIRouter(
    prefix="/api/v1/coaches",
    tags=["coaches"]
)

@router.get("/", response_model=List[CoachScheduleResponse])
def get_coaches(db: Session = Depends(get_db)):
    """
    Get all coaches with their schedules
    """
    return db.query(Coach).all()

@router.post("/", response_model=CoachScheduleResponse)
def create_coach(coach: CoachCreate, db: Session = Depends(get_db)):
    """
    Create a new coach
    """
    db_coach = Coach(**coach.dict())
    db.add(db_coach)
    db.commit()
    db.refresh(db_coach)
    return db_coach

@router.put("/{coach_id}", response_model=CoachScheduleResponse)
def update_coach(coach_id: int, coach: CoachUpdate, db: Session = Depends(get_db)):
    """
    Update coach information
    """
    db_coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not db_coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    
    for key, value in coach.dict().items():
        if value is not None:
            setattr(db_coach, key, value)
    
    db.commit()
    db.refresh(db_coach)
    return db_coach

@router.delete("/{coach_id}")
def delete_coach(coach_id: int, db: Session = Depends(get_db)):
    """
    Delete a coach
    """
    db_coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not db_coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    
    db.delete(db_coach)
    db.commit()
    return {"message": "Coach deleted successfully"}

@router.get("/schedules", response_model=List[CoachScheduleResponse])
def get_coach_schedules(db: Session = Depends(get_db)):
    """
    Get all coach schedules with coach details
    """
    return db.query(CoachSchedule).join(Coach).all()

@router.get("/schedules/{coach_id}", response_model=List[CoachScheduleResponse])
def get_coach_schedules_by_id(coach_id: int, db: Session = Depends(get_db)):
    """
    Get schedules for a specific coach
    """
    return db.query(CoachSchedule).filter(CoachSchedule.coach_id == coach_id).all()

@router.get("/schedules/date/{date}", response_model=List[CoachScheduleResponse])
def get_coach_schedules_by_date(date: str, db: Session = Depends(get_db)):
    """
    Get schedules for a specific date
    """
    try:
        schedule_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
    return db.query(CoachSchedule).filter(CoachSchedule.date == schedule_date).all()
def get_coach_schedules_by_id(coach_id: int, db: Session = Depends(get_db)):
    """
    Get schedules for a specific coach
    """
    return db.query(CoachSchedule).filter(CoachSchedule.coach_id == coach_id).all()
def get_coach_schedules(db: Session = Depends(get_db)):
    """
    Get all coach schedules
    """
    return db.query(CoachSchedule).all()

@router.post("/schedules", response_model=CoachScheduleResponse)
def create_coach_schedule(schedule: CoachScheduleCreate, db: Session = Depends(get_db)):
    """
    Create a new coach schedule
    """
    db_schedule = CoachSchedule(**schedule.dict())
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule

@router.put("/schedules/{schedule_id}", response_model=CoachScheduleResponse)
def update_coach_schedule(schedule_id: int, schedule: CoachScheduleCreate, db: Session = Depends(get_db)):
    """
    Update coach schedule with validation
    """
    db_schedule = db.query(CoachSchedule).filter(CoachSchedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Validate coach exists
    coach = db.query(Coach).filter(Coach.id == schedule.coach_id).first()
    if not coach:
        raise HTTPException(status_code=400, detail="Invalid coach_id")

    for key, value in schedule.dict().items():
        if value is not None:
            setattr(db_schedule, key, value)

    db.commit()
    db.refresh(db_schedule)
    return db_schedule

@router.delete("/schedules/{schedule_id}")
def delete_coach_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """
    Delete a coach schedule
    """
    db_schedule = db.query(CoachSchedule).filter(CoachSchedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    db.delete(db_schedule)
    db.commit()
    return {"message": "Schedule deleted successfully"}
def update_coach_schedule(schedule_id: int, schedule: CoachScheduleCreate, db: Session = Depends(get_db)):
    """
    Update coach schedule
    """
    db_schedule = db.query(CoachSchedule).filter(CoachSchedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    for key, value in schedule.dict().items():
        if value is not None:
            setattr(db_schedule, key, value)
    
    db.commit()
    db.refresh(db_schedule)
    return db_schedule