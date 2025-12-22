from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import BackgroundTasks
from contextlib import contextmanager
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from ..database import get_db
from ..redis import redis_client
from ..models import Course, CourseSchedule, CourseBooking, Member
from ..utils import logger
from ..schemas import CourseCreate, CourseBookingCreate
from ..exceptions import ConcurrencyException

router = APIRouter(
    prefix="/api/v1/courses",
    tags=["courses"]
)

@router.get("/", response_model=List[Course])
# Constants for course statuses and lock settings
CONFIRMED_STATUS = "confirmed"
CANCELLED_STATUS = "cancelled"
BOOKING_LOCK_TIMEOUT = 10  # seconds
BOOKING_LOCK_BLOCKING_TIMEOUT = 5  # seconds

def get_courses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get all courses
    """
    courses = db.query(Course).offset(skip).limit(limit).all()
    return courses

@router.post("/", response_model=Course, status_code=status.HTTP_201_CREATED)
def create_course(course: CourseCreate, db: Session = Depends(get_db)):
    """
    Create a new course
    """
    db_course = Course(**course.dict())
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course

@router.get("/schedule", response_model=List[CourseSchedule])
def get_course_schedules(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get all course schedules
    """
    schedules = db.query(CourseSchedule).offset(skip).limit(limit).all()
    return schedules

@router.get("/{course_id}/bookings", response_model=List[CourseBooking])
def get_course_bookings(course_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get all bookings for a specific course with pagination
    """
    # Check if schedule exists first
    if not db.query(CourseSchedule).filter(CourseSchedule.id == course_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course schedule not found")
        
    bookings = db.query(CourseBooking).filter(
        CourseBooking.schedule_id == course_id
    ).offset(skip).limit(limit).all()
    return bookings

@contextmanager
def acquire_lock(lock_key: str, timeout: int = 10, blocking_timeout: int = 5):
    """
    Context manager for acquiring and releasing Redis locks
    
    Args:
        lock_key: Redis lock key
        timeout: Lock timeout in seconds
        blocking_timeout: Maximum time to wait for lock acquisition
    
    Yields:
        bool: True if lock acquired, False otherwise
    """
    lock = redis_client.lock(lock_key, timeout=timeout, blocking_timeout=blocking_timeout)
    acquired = False
    try:
        acquired = lock.acquire()
        yield acquired
    finally:
        if acquired:
            lock.release()
@router.post("/{course_id}/bookings", response_model=CourseBooking, status_code=status.HTTP_201_CREATED)
def book_course(
    course_id: int, 
    booking: CourseBookingCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Book a course
    
    - Checks member existence
    - Validates schedule availability
    - Prevents duplicate bookings
    """
    # Acquire distributed lock to prevent concurrent bookings
    lock_key = f"course_booking_lock:{course_id}"
    lock = redis_client.lock(
        lock_key,
        timeout=BOOKING_LOCK_TIMEOUT,
        blocking_timeout=BOOKING_LOCK_BLOCKING_TIMEOUT
    )
    
    try:
        if not lock.acquire():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Another booking is in progress. Please try again."
            )
        # Check if member exists
        member = db.query(Member).filter(Member.id == booking.member_id).first()
        if not member or not member.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Member not found or inactive"
            )
    
        # Check if schedule exists
        schedule = db.query(CourseSchedule).filter(CourseSchedule.id == course_id).first()
        if not schedule or schedule.is_full:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Course schedule not found or already full"
            )
    
        # Check if already booked
        existing_booking = db.query(CourseBooking).filter(
            CourseBooking.member_id == booking.member_id,
            CourseBooking.schedule_id == course_id
        ).first()
    
        if existing_booking and existing_booking.status == CONFIRMED_STATUS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already booked this course"
            )
    
        # Create booking
        db_booking = CourseBooking(
            member_id=booking.member_id,
            schedule_id=course_id,
            status=CONFIRMED_STATUS
        )
        db.add(db_booking)
        db.commit()
        db.refresh(db_booking)
        
        # Release the lock after successful booking
        lock.release()
        
        # Add background task to update course capacity
        background_tasks.add_task(
            update_course_capacity,
            course_id=course_id,
            db=db
        )
    except Exception as e:
        if lock.locked:
            lock.release()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Booking failed: {str(e)}"
        )
    return db_booking

@router.delete("/{course_id}/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_booking(course_id: int, booking_id: int, db: Session = Depends(get_db)):
    """
    Cancel a course booking
    
    - Validates booking existence
    - Ensures proper ownership
    """
    booking = db.query(CourseBooking).filter(
        CourseBooking.id == booking_id,
        CourseBooking.schedule_id == course_id
    ).first()
    
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    
    db.delete(booking)
    db.commit()
    return None

def update_course_capacity(course_id: int, db: Session):
    """
    Background task to update course capacity after booking
    
    Features:
    - Atomic capacity updates
    - Automatic full status management
    - Error resilience with logging
    """
    """
    Background task to update course capacity after booking
    """
    try:
        # Get current booking count
        booking_count = db.query(func.count(CourseBooking.id)).filter(
            CourseBooking.schedule_id == course_id,
            CourseBooking.status == CONFIRMED_STATUS
        ).scalar()
        
        # Get course capacity
        schedule = db.query(CourseSchedule).filter(
            CourseSchedule.id == course_id
        ).first()
        
        if schedule:
            course = db.query(Course).filter(
                Course.id == schedule.course_id
            ).first()
            
            if course and booking_count >= course.capacity:
                # Update schedule status if full
                schedule.is_full = True
                db.commit()
    except Exception as e:
        # Log error but don't fail the booking
        pass

