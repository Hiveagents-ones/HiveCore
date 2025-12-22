from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from .... import crud, schemas, models
from ....database import get_db

router = APIRouter()


@router.get("/", response_model=List[schemas.Course])
def read_courses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    coach_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Retrieve courses with pagination support.
    """
    courses = crud.get_courses(db, skip=skip, limit=limit, coach_id=coach_id)
    return courses


@router.post("/", response_model=schemas.Course)
def create_course(course: schemas.CourseCreate, db: Session = Depends(get_db)):
    """
    Create a new course.
    """
    # Check if coach exists
    coach = crud.get_user(db, user_id=course.coach_id)
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    
    # Check coach availability
    is_available = crud.check_coach_availability(
        db, coach_id=course.coach_id, 
        start_time=course.start_time, 
        end_time=course.end_time
    )
    if not is_available:
        raise HTTPException(
            status_code=409, 
            detail="Coach is not available during the requested time slot"
        )
    
    return crud.create_course(db=db, course=course)


@router.get("/{course_id}", response_model=schemas.Course)
def read_course(course_id: int, db: Session = Depends(get_db)):
    """
    Get a specific course by ID.
    """
    db_course = crud.get_course(db, course_id=course_id)
    if db_course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return db_course


@router.put("/{course_id}", response_model=schemas.Course)
def update_course(
    course_id: int, 
    course: schemas.CourseUpdate, 
    db: Session = Depends(get_db)
):
    """
    Update a course.
    """
    db_course = crud.get_course(db, course_id=course_id)
    if db_course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if coach exists (if coach_id is being updated)
    if course.coach_id is not None:
        coach = crud.get_user(db, user_id=course.coach_id)
        if not coach:
            raise HTTPException(status_code=404, detail="Coach not found")
    
    # Check coach availability for time conflicts
    start_time = course.start_time if course.start_time is not None else db_course.start_time
    end_time = course.end_time if course.end_time is not None else db_course.end_time
    coach_id = course.coach_id if course.coach_id is not None else db_course.coach_id
    
    is_available = crud.check_coach_availability(
        db, coach_id=coach_id, 
        start_time=start_time, 
        end_time=end_time,
        exclude_course_id=course_id
    )
    if not is_available:
        raise HTTPException(
            status_code=409, 
            detail="Coach is not available during the requested time slot"
        )
    
    return crud.update_course(db, course_id=course_id, course=course)


@router.delete("/{course_id}", response_model=schemas.Course)
def delete_course(course_id: int, db: Session = Depends(get_db)):
    """
    Delete a course.
    """
    db_course = crud.get_course(db, course_id=course_id)
    if db_course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return crud.delete_course(db, course_id=course_id)
