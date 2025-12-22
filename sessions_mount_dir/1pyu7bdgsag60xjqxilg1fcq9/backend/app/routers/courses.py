from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..models.course import Course
from ..database import get_db

router = APIRouter(
    prefix="/api/v1/courses",
    tags=["courses"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[Course])
def list_courses(db: Session = Depends(get_db)):
    """
    Get list of all available courses
    """
    return db.query(Course).all()


@router.post("/", response_model=Course)
def create_course(course: Course, db: Session = Depends(get_db)):
    """
    Create a new course
    """
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.get("/{course_id}", response_model=Course)
def get_course(course_id: int, db: Session = Depends(get_db)):
    """
    Get course details by ID
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.put("/{course_id}", response_model=Course)
def update_course(course_id: int, course: Course, db: Session = Depends(get_db)):
    """
    Update course information
    """
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    for field, value in course.dict().items():
        setattr(db_course, field, value)
    
    db.commit()
    db.refresh(db_course)
    return db_course


@router.delete("/{course_id}")
def delete_course(course_id: int, db: Session = Depends(get_db)):
    """
    Delete a course
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    db.delete(course)
    db.commit()
    return {"message": "Course deleted successfully"}