from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import (
    Coach,
    CoachCreate,
    CoachUpdate,
    CoachSchedule,
    CoachScheduleCreate,
    CoachScheduleUpdate
)
from ..models import Coach as CoachModel, CoachSchedule as CoachScheduleModel
from ..middlewares.security import JWTBearer, ROLES
from ..models import CoachAvailability as CoachAvailabilityModel

router = APIRouter(
    prefix="/api/v1/coaches",
    tags=["coaches"]
)


@router.post("/", response_model=Coach)
def create_coach(coach: CoachCreate, db: Session = Depends(get_db)):
    db_coach = CoachModel(**coach.dict())
    db.add(db_coach)
    db.commit()
    db.refresh(db_coach)
    return db_coach


@router.get("/", response_model=List[Coach])
def read_coaches(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    coaches = db.query(CoachModel).offset(skip).limit(limit).all()
    return coaches


@router.get("/{coach_id}", response_model=Coach)
def read_coach(coach_id: int, db: Session = Depends(get_db)):
    db_coach = db.query(CoachModel).filter(CoachModel.id == coach_id).first()
    if db_coach is None:
        raise HTTPException(status_code=404, detail="Coach not found")
    return db_coach


@router.put("/{coach_id}", response_model=Coach)
def update_coach(coach_id: int, coach: CoachUpdate, db: Session = Depends(get_db)):
    db_coach = db.query(CoachModel).filter(CoachModel.id == coach_id).first()
    if db_coach is None:
        raise HTTPException(status_code=404, detail="Coach not found")
    
    update_data = coach.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_coach, key, value)
    
    db.add(db_coach)
    db.commit()
    db.refresh(db_coach)
    return db_coach


@router.delete("/{coach_id}")
def delete_coach(coach_id: int, db: Session = Depends(get_db)):
    db_coach = db.query(CoachModel).filter(CoachModel.id == coach_id).first()
    if db_coach is None:
        raise HTTPException(status_code=404, detail="Coach not found")
    
    db.delete(db_coach)
    db.commit()
    return {"message": "Coach deleted successfully"}


# Coach Schedule Endpoints
@router.post(
    "/{coach_id}/schedules", 
    response_model=CoachSchedule,
    dependencies=[Depends(JWTBearer(allowed_roles=[ROLES['ADMIN'], ROLES['COACH']]))],
    status_code=status.HTTP_201_CREATED
)
def create_coach_schedule(
    """
    Create a new coach schedule with the following checks:
    - Only admin or the coach themselves can create schedules
    - Validate time range (end_time > start_time)
    - Check for overlapping schedules
    - Validate coach is active
    - Validate schedule is in the future
    """
    coach_id: int, 
    schedule: CoachScheduleCreate, 
    db: Session = Depends(get_db),
    token_data: dict = Depends(JWTBearer(allowed_roles=[ROLES['ADMIN'], ROLES['COACH']]))
):
    # Check for schedule conflicts
    # Validate time range
    if schedule.start_time >= schedule.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time"
        )
    
    # Validate schedule duration
    duration = (schedule.end_time - schedule.start_time).total_seconds() / 60
    if duration < 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule duration must be at least 30 minutes"
        )
    if duration > 480:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule duration cannot exceed 8 hours"
        )

    # Check coach exists and is active
    db_coach = db.query(CoachModel).filter(CoachModel.id == coach_id).first()
    if not db_coach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coach not found"
        )
    if not db_coach.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coach is not active"
        )

    # Validate time range
    if schedule.end_time <= schedule.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time"
        )

    # Check for overlapping schedules with buffer time (15 minutes)
    buffer_time = timedelta(minutes=15)
    conflicting_schedules = db.query(CoachScheduleModel).filter(
        CoachScheduleModel.coach_id == coach_id,
        CoachScheduleModel.start_time < schedule.end_time + buffer_time,
        CoachScheduleModel.end_time > schedule.start_time - buffer_time
    ).first()
    
    if conflicting_schedules:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Coach already has a schedule during this time"
        )
    
    db_schedule = CoachScheduleModel(**schedule.dict(), coach_id=coach_id)
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule


@router.get(
    "/{coach_id}/schedules", 
    response_model=List[CoachSchedule],
    dependencies=[Depends(JWTBearer(allowed_roles=[ROLES['ADMIN'], ROLES['COACH'], ROLES['MEMBER']]))],
    description="Get coach schedules with optional date range filtering"
)
def read_coach_schedules(
    coach_id: int, 
    skip: int = 0, 
    limit: int = 100,
    start_date: datetime = None,
    end_date: datetime = None, 
    db: Session = Depends(get_db)
):
    query = db.query(CoachScheduleModel)\
        .filter(CoachScheduleModel.coach_id == coach_id)
        
    if start_date:
        query = query.filter(CoachScheduleModel.start_time >= start_date)
    if end_date:
        query = query.filter(CoachScheduleModel.end_time <= end_date)
        
    schedules = query.offset(skip).limit(limit).all()
    return schedules


@router.put(
    "/schedules/{schedule_id}", 
    response_model=CoachSchedule,
    dependencies=[Depends(JWTBearer(allowed_roles=[ROLES['ADMIN'], ROLES['COACH']]))],
    status_code=status.HTTP_200_OK
)



@router.delete(
    "/schedules/{schedule_id}",
    dependencies=[Depends(JWTBearer(allowed_roles=[ROLES['ADMIN'], ROLES['COACH']]))],
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_coach_schedule(
    schedule_id: int, 
    db: Session = Depends(get_db),
    token_data: dict = Depends(JWTBearer(allowed_roles=[ROLES['ADMIN'], ROLES['COACH']]))
):
    db_schedule = db.query(CoachScheduleModel)\
        .filter(CoachScheduleModel.id == schedule_id)\
        .first()
        
    if db_schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
        
    # Check if requester is coach and matches schedule's coach_id
    if token_data['role'] == ROLES['COACH'] and token_data['user_id'] != db_schedule.coach_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete schedule for another coach"
        )

    if db_schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    db.delete(db_schedule)
    db.commit()
    return {"message": "Schedule deleted successfully"}
def update_coach_schedule(
    """
    Update an existing coach schedule with the following checks:
    - Only admin or the coach themselves can update schedules
    - Validate time range (end_time > start_time)
    - Check for overlapping schedules (excluding current schedule)
    """
    schedule_id: int, 
    schedule: CoachScheduleUpdate, 
    db: Session = Depends(get_db)
):
    db_schedule = db.query(CoachScheduleModel)\
        .filter(CoachScheduleModel.id == schedule_id)\
        .first()
    
    if db_schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Check for schedule conflicts (excluding current schedule)
    conflicting_schedules = db.query(CoachScheduleModel).filter(
        CoachScheduleModel.coach_id == db_schedule.coach_id,
        CoachScheduleModel.id != schedule_id,
        CoachScheduleModel.start_time < schedule.end_time,
        CoachScheduleModel.end_time > schedule.start_time
    ).first()
    
    if conflicting_schedules:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Coach already has another schedule during this time"
        )
    
    update_data = schedule.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_schedule, key, value)
    
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule


# Coach Availability Endpoints
@router.post("/{coach_id}/availability", response_model=CoachAvailabilityResponse)
def create_coach_availability(
    coach_id: int, 
    availability: CoachAvailabilityCreate, 
    db: Session = Depends(get_db)
):
    db_availability = CoachAvailabilityModel(**availability.dict(), coach_id=coach_id)
    db.add(db_availability)
    db.commit()
    db.refresh(db_availability)
    return db_availability


@router.get("/{coach_id}/availability", response_model=List[CoachAvailabilityResponse])
def read_coach_availability(
    coach_id: int, 
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    availability = db.query(CoachAvailabilityModel)\n        .filter(CoachAvailabilityModel.coach_id == coach_id)\n        .offset(skip)\n        .limit(limit)\n        .all()
    return availability


@router.put("/availability/{availability_id}", response_model=CoachAvailabilityResponse)
def update_coach_availability(
    availability_id: int, 
    availability: CoachAvailabilityUpdate, 
    db: Session = Depends(get_db)
):
    db_availability = db.query(CoachAvailabilityModel)\n        .filter(CoachAvailabilityModel.id == availability_id)\n        .first()

    if db_availability is None:
        raise HTTPException(status_code=404, detail="Availability not found")

    update_data = availability.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_availability, key, value)

    db.add(db_availability)
    db.commit()
    db.refresh(db_availability)
    return db_availability


@router.delete("/availability/{availability_id}")
def delete_coach_availability(
    availability_id: int, 
    db: Session = Depends(get_db)
):
    db_availability = db.query(CoachAvailabilityModel)\n        .filter(CoachAvailabilityModel.id == availability_id)\n        .first()

    if db_availability is None:
        raise HTTPException(status_code=404, detail="Availability not found")

    db.delete(db_availability)
    db.commit()
    return {"message": "Availability deleted successfully"}

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
@router.post("/{coach_id}/schedules", 
    response_model=CoachSchedule,
    dependencies=[Depends(JWTBearer(allowed_roles=[ROLES['ADMIN'], ROLES['COACH']]))],
    status_code=status.HTTP_201_CREATED
)
def create_coach_schedule(
    """
    Create a new coach schedule with the following checks:
    - Only admin or the coach themselves can create schedules
    - Validate time range (end_time > start_time)
    - Check for overlapping schedules
    - Validate coach is active
    - Validate schedule is in the future
    - Validate schedule duration (min 30min, max 8h)
    """
    coach_id: int, 
    schedule: CoachScheduleCreate, 
    db: Session = Depends(get_db),
    token_data: dict = Depends(JWTBearer(allowed_roles=[ROLES['ADMIN'], ROLES['COACH']]))
):
    # Check if coach is active
    db_coach = db.query(CoachModel).filter(CoachModel.id == coach_id).first()
    if not db_coach or not db_coach.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coach is not active or does not exist"
        )

    # Check if requester is coach and matches coach_id
    if token_data['role'] == ROLES['COACH'] and token_data['user_id'] != coach_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create schedule for another coach"
        )

    # Validate schedule is in the future
    if schedule.start_time < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create schedule in the past"
        )

# [AUTO-APPENDED] Failed to insert:

    # Check if requester is coach and matches schedule's coach_id
    if token_data['role'] == ROLES['COACH'] and token_data['user_id'] != db_schedule.coach_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update schedule for another coach"
        )

    # Validate schedule is in the future
    if schedule.end_time < datetime.now() or schedule.start_time < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update schedule to be in the past"
        )

# [AUTO-APPENDED] Failed to insert:

    # Check if coach is active
    if not db_coach.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coach is not active"
        )

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
@router.put("/schedules/{schedule_id}", response_model=CoachSchedule,
    dependencies=[Depends(JWTBearer(allowed_roles=[ROLES['ADMIN'], ROLES['COACH']]))])
def update_coach_schedule(
    """
    Update an existing coach schedule with the following checks:
    - Only admin or the coach themselves can update schedules
    - Validate time range (end_time > start_time)
    - Check for overlapping schedules (excluding current schedule)
    - Validate schedule duration (min 30min, max 8h)
    - Validate schedule is in the future
    """
    schedule_id: int, 
    schedule: CoachScheduleUpdate, 
    db: Session = Depends(get_db),
    token_data: dict = Depends(JWTBearer(allowed_roles=[ROLES['ADMIN'], ROLES['COACH']]))
):
    db_schedule = db.query(CoachScheduleModel).filter(CoachScheduleModel.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
        
    # Check coach is active
    db_coach = db.query(CoachModel).filter(CoachModel.id == db_schedule.coach_id).first()
    if not db_coach or not db_coach.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coach is not active"
        )

    # Check if requester is coach and matches schedule's coach_id
    if token_data['role'] == ROLES['COACH'] and token_data['user_id'] != db_schedule.coach_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update schedule for another coach"
        )

    # Validate schedule is in the future
    if (schedule.end_time and schedule.end_time < datetime.now()) or \
       (schedule.start_time and schedule.start_time < datetime.now()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update schedule to be in the past"
        )

    # Check for schedule conflicts with buffer time (excluding current schedule)
    if schedule.start_time or schedule.end_time:
        start_time = schedule.start_time if schedule.start_time else db_schedule.start_time
        end_time = schedule.end_time if schedule.end_time else db_schedule.end_time
        
        # Validate schedule duration
        duration = (end_time - start_time).total_seconds() / 60
        if duration < 30:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Schedule duration must be at least 30 minutes"
            )
        if duration > 480:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Schedule duration cannot exceed 8 hours"
            )
        
        buffer_time = timedelta(minutes=15)
        
        if start_time >= end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End time must be after start time"
            )
            
        conflicting_schedules = db.query(CoachScheduleModel).filter(
            CoachScheduleModel.coach_id == db_schedule.coach_id,
            CoachScheduleModel.id != schedule_id,
            CoachScheduleModel.start_time < end_time + buffer_time,
            CoachScheduleModel.end_time > start_time - buffer_time
        ).first()
        
        if conflicting_schedules:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Schedule conflicts with existing schedule"
            )

    update_data = schedule.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_schedule, key, value)

    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule