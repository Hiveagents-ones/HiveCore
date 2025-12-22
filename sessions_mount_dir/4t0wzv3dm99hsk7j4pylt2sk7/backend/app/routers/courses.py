from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
from ..database import get_db
from ..models import User, Course
from ..schemas import Course as CourseSchema, CourseCreate, CourseUpdate
from ..core.security import get_current_user, require_permission, require_ownership_or_permission

router = APIRouter(prefix="/courses", tags=["courses"])

@router.get("/", response_model=List[CourseSchema])
def get_courses(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ownership_or_permission("courses", "read"))
):
    # If user is a coach, only show their courses
    if "coach" in [role.name for role in current_user.roles]:
        courses = db.query(Course).filter(Course.coach_id == current_user.id).offset(skip).limit(limit).all()
    else:
        courses = db.query(Course).offset(skip).limit(limit).all()
    return courses

@router.post("/", response_model=CourseSchema)
def create_course(
    course: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("courses", "create"))
):
    db_course = Course(**course.model_dump())
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course

@router.get("/{course_id}", response_model=CourseSchema)
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ownership_or_permission("courses", "read"))
):
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if user is the coach of this course
    if "coach" in [role.name for role in current_user.roles] and db_course.coach_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this course")
    
    return db_course

@router.put("/{course_id}", response_model=CourseSchema)
def update_course(
    course_id: int,
    course_update: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ownership_or_permission("courses", "update"))
):
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if user is the coach of this course
    if "coach" in [role.name for role in current_user.roles] and db_course.coach_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this course")
    
    update_data = course_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_course, field, value)
    
    db.commit()
    db.refresh(db_course)
    return db_course

@router.delete("/{course_id}")
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ownership_or_permission("courses", "delete"))
):
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if user is the coach of this course
    if "coach" in [role.name for role in current_user.roles] and db_course.coach_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this course")
    
    db.delete(db_course)
    db.commit()
    return {"message": "Course deleted successfully"}

@router.get("/coach/my-courses", response_model=List[CourseSchema])
def get_my_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user is a coach
    if "coach" not in [role.name for role in current_user.roles]:
        raise HTTPException(status_code=403, detail="User is not a coach")
    
    courses = db.query(Course).filter(Course.coach_id == current_user.id).all()
    return courses