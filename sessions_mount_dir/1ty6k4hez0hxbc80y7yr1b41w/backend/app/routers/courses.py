from fastapi import APIRouter, Depends, HTTPException
from fastapi import status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..database import RedisCache
from ..database import get_redis
from ..models import Course, CoachSchedule
from ..schemas import CourseCreate, CourseResponse

router = APIRouter(
    prefix="/api/v1/courses",
    tags=["courses"]
)


@router.get("/", response_model=List[CourseResponse])
def get_courses(db: Session = Depends(get_db)):
    """
    Get all available courses
    """
    return db.query(Course).all()


@router.post("/", response_model=CourseResponse)
def create_course(course: CourseCreate, db: Session = Depends(get_db)):
    """
    Create a new course
    """
    # Check if coach schedule exists
    coach_schedule = db.query(CoachSchedule).filter(
        CoachSchedule.id == course.coach_schedule_id
    ).first()
    
    if not coach_schedule:
        raise HTTPException(
            status_code=400,
            detail="Coach schedule not found"
        )
    
    # Check if coach is available at this time
    conflicting_courses = db.query(Course).filter(
        Course.coach_schedule_id == course.coach_schedule_id
    ).count()
    
    if conflicting_courses > 0:
        raise HTTPException(
            status_code=400,
            detail="Coach already has a course scheduled at this time"
        )
    
    db_course = Course(
        name=course.name,
        coach_schedule_id=course.coach_schedule_id,
        max_members=course.max_members
    )
    
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    
    return db_course