from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request
from fastapi import status
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import CoachSchedule
from ..models import CoachScheduleLog
from ..schemas import CoachScheduleCreate, CoachScheduleUpdate, CoachScheduleResponse
from ..schemas import CoachScheduleLogCreate
from ..auth import get_current_user
from ..services.audit_log import AuditLogService
from typing import Optional

router = APIRouter(
    prefix="/api/v1/coaches/schedules",
    tags=["coaches"]
)

@router.get("/", response_model=List[CoachScheduleResponse])
def get_coach_schedules(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get all coach schedules
    """
    schedules = db.query(CoachSchedule).offset(skip).limit(limit).all()
    return schedules

@router.post("/", response_model=CoachScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_coach_schedule(
    schedule: CoachScheduleCreate, 
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new coach schedule
    """
    # Check for schedule conflicts
    conflicting_schedules = db.query(CoachSchedule).filter(
        CoachSchedule.coach_id == schedule.coach_id,
        CoachSchedule.start_time < schedule.end_time,
        CoachSchedule.end_time > schedule.start_time
    ).all()
    
    if conflicting_schedules:
        logging.warning(f"Schedule conflict detected for coach {schedule.coach_id}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Coach already has a schedule during this time"
        )
    db_schedule = CoachSchedule(**schedule.dict())
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    # Log the schedule update
    log_entry = CoachScheduleLogCreate(
        schedule_id=schedule_id,
        action="update",
        changed_by=current_user.get("id"),
        old_values=old_values,
        new_values=schedule.dict(exclude_unset=True)
    )
    db_log = CoachScheduleLog(**log_entry.dict())
    db.add(db_log)
    db.commit()
    
    logging.info(f"Updated schedule {schedule_id}")
    # Log the schedule creation
    log_entry = CoachScheduleLogCreate(
        schedule_id=db_schedule.id,
        action="create",
        changed_by=current_user.get("id"),
        old_values={},
        new_values=schedule.dict()
    )
    db_log = CoachScheduleLog(**log_entry.dict())
    db.add(db_log)
    db.commit()
    
    logging.info(f"Created new schedule for coach {schedule.coach_id}")
    
    # Log to audit system
    AuditLogService.log_schedule_action(
        db=db,
        action="create",
        schedule_id=db_schedule.id,
        coach_id=schedule.coach_id,
        changed_by=current_user.get("id"),
        old_values=None,
        new_values=schedule.dict()
    )
    
    return db_schedule

@router.get("/{schedule_id}", response_model=CoachScheduleResponse)
def get_coach_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """
    Get a specific coach schedule by ID
    """
    schedule = db.query(CoachSchedule).filter(CoachSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule

@router.put("/{schedule_id}", response_model=CoachScheduleResponse)
def update_coach_schedule(
    schedule_id: int, 
    schedule: CoachScheduleUpdate, 
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update a coach schedule
    """
    db_schedule = db.query(CoachSchedule).filter(CoachSchedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Check for schedule conflicts if time is being updated
    if schedule.start_time or schedule.end_time:
        new_start = schedule.start_time if schedule.start_time else db_schedule.start_time
        new_end = schedule.end_time if schedule.end_time else db_schedule.end_time
        
        conflicting_schedules = db.query(CoachSchedule).filter(
            CoachSchedule.coach_id == db_schedule.coach_id,
            CoachSchedule.id != schedule_id,
            CoachSchedule.start_time < new_end,
            CoachSchedule.end_time > new_start
        ).all()
        
        if conflicting_schedules:
            logging.warning(f"Schedule conflict detected when updating schedule {schedule_id}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Coach already has a schedule during this time"
            )
    
    old_values = {
        "start_time": db_schedule.start_time,
        "end_time": db_schedule.end_time,
        "available": db_schedule.available
    }
    for key, value in schedule.dict(exclude_unset=True).items():
        setattr(db_schedule, key, value)
    
    db.commit()
    db.refresh(db_schedule)
    
    # Log to audit system
    AuditLogService.log_schedule_action(
        db=db,
        action="update",
        schedule_id=schedule_id,
        coach_id=db_schedule.coach_id,
        changed_by=current_user.get("id"),
        old_values=old_values,
        new_values=schedule.dict(exclude_unset=True)
    )
    
    return db_schedule

@router.delete("/{schedule_id}")
def delete_coach_schedule(
    schedule_id: int, 
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a coach schedule
    """
    schedule = db.query(CoachSchedule).filter(CoachSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    db.delete(schedule)
    # Log the schedule deletion
    log_entry = CoachScheduleLogCreate(
        schedule_id=schedule_id,
        action="delete",
        changed_by=current_user.get("id"),
        old_values={
            "coach_id": schedule.coach_id,
            "start_time": schedule.start_time,
            "end_time": schedule.end_time,
            "available": schedule.available
        },
        new_values={}
    )
    db_log = CoachScheduleLog(**log_entry.dict())
    db.add(db_log)
    
    logging.info(f"Deleted schedule {schedule_id}")
    
    # Log to audit system
    AuditLogService.log_schedule_action(
        db=db,
        action="delete",
        schedule_id=schedule_id,
        coach_id=schedule.coach_id,
        changed_by=current_user.get("id"),
        old_values={
            "coach_id": schedule.coach_id,
            "start_time": schedule.start_time,
            "end_time": schedule.end_time,
            "available": schedule.available
        },
        new_values={}
    )
    
    db.commit()
    return {"message": "Schedule deleted successfully"}

@router.get("/logs/{schedule_id}", response_model=List[CoachScheduleLog])
def get_schedule_logs(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get change logs for a specific schedule
    """
    logs = db.query(CoachScheduleLog).filter(
        CoachScheduleLog.schedule_id == schedule_id
    ).order_by(CoachScheduleLog.changed_at.desc()).all()
    
    if not logs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No logs found for this schedule"
        )
    
    return logs