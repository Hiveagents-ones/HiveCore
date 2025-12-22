from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from typing import List

from ..database import get_db
from ..schemas.courses import Course, CourseCreate, CourseUpdate, CourseBooking
from ..database import Course as DBCourse, Member, Coach
from sqlalchemy.exc import IntegrityError

router = APIRouter(
    prefix="/api/v1/courses",
    tags=["courses"]
)


@router.get("/", response_model=List[Course])
def get_courses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get all courses with pagination
    """
    courses = db.query(DBCourse).offset(skip).limit(limit).all()
    return courses


@router.post("/", response_model=Course, status_code=status.HTTP_201_CREATED)
def create_course(course: CourseCreate, db: Session = Depends(get_db)):
    """
    Create a new course
    """
    # Check if coach exists
    coach = db.query(Coach).filter(Coach.id == course.coach_id).first()
    if not coach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coach not found"
        )
    
    db_course = DBCourse(
        name=course.name,
        description=course.description,
        start_time=course.start_time,
        end_time=course.end_time,
        coach_id=course.coach_id,
        capacity=course.max_capacity,
        booked=course.current_enrollment
    )
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course


@router.get("/{course_id}", response_model=Course)
def get_course(course_id: int, db: Session = Depends(get_db)):
    """
    Get a specific course by ID
    """
    course = db.query(DBCourse).filter(DBCourse.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    return course


@router.put("/{course_id}", response_model=Course)
def update_course(course_id: int, course: CourseUpdate, db: Session = Depends(get_db)):
    """
    Update a course
    """
    db_course = db.query(DBCourse).filter(DBCourse.id == course_id).first()
    if not db_course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    if course.name is not None:
        db_course.name = course.name
    if course.description is not None:
        db_course.description = course.description
    if course.start_time is not None:
        db_course.start_time = course.start_time
    if course.end_time is not None:
        db_course.end_time = course.end_time
    if course.coach_id is not None:
        # Verify coach exists
        coach = db.query(Coach).filter(Coach.id == course.coach_id).first()
        if not coach:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Coach not found"
            )
        db_course.coach_id = course.coach_id
    if course.max_capacity is not None:
        db_course.capacity = course.max_capacity
    if course.current_enrollment is not None:
        db_course.booked = course.current_enrollment
    
    db.commit()
    db.refresh(db_course)
    return db_course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: int, db: Session = Depends(get_db)):
    """
    Delete a course
    """
    course = db.query(DBCourse).filter(DBCourse.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    db.delete(course)
    db.commit()
    return None


@router.post("/{course_id}/book", status_code=status.HTTP_201_CREATED)
def book_course(course_id: int, booking: CourseBooking, db: Session = Depends(get_db)):
    """
    Book a course for a member
    """
    # Check if course exists
    course = db.query(DBCourse).filter(DBCourse.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Check if member exists
    member = db.query(Member).filter(Member.id == booking.member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # Check if course has available slots
    if course.booked >= course.capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course is fully booked"
        )
    
    # Update booking count
    course.booked += 1
    db.commit()
    
    return {"message": "Course booked successfully"}