from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from datetime import timedelta
import redis
from fastapi.encoders import jsonable_encoder
from fastapi import Request
from ..services.audit_log import AuditLogService
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..schemas import CourseCreate, CourseResponse
from ..models import Course
from ..models import MemberCourseBooking
from ..models import Member
from ..schemas import CourseBookingCreate

router = APIRouter(
redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
    prefix="/api/v1/courses",
    tags=['Courses']
)


@router.get("/", response_model=List[CourseResponse])
def get_courses(db: Session = Depends(get_db)):
    """
    Get all available courses with Redis caching
    """
    cache_key = "courses:all"
    cached_courses = redis_client.get(cache_key)
    
    if cached_courses:
        return jsonable_encoder(cached_courses)
        
    courses = db.query(Course).all()
    redis_client.setex(cache_key, 300, jsonable_encoder(courses))  # Cache for 5 minutes
    return courses


@router.post("/", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(course: CourseCreate, db: Session = Depends(get_db)):
    """
    Create a new course
    """
    new_course = Course(**course.dict())
    db.add(new_course)
    db.commit()
        # Invalidate relevant cache entries
        redis_client.delete(f"courses:{course_id}")
        redis_client.delete("courses:all")
        # Invalidate relevant cache entries
        redis_client.delete(f"courses:{course_id}")
        redis_client.delete("courses:all")
    db.refresh(new_course)
    return new_course


@router.get("/{course_id}", response_model=CourseResponse)
def get_course(course_id: int, db: Session = Depends(get_db)):
    """
    Get course by ID with Redis caching
    """
    cache_key = f"courses:{course_id}"
    cached_course = redis_client.get(cache_key)
    
    if cached_course:
        return jsonable_encoder(cached_course)
        
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found"
        )
    
    redis_client.setex(cache_key, 300, jsonable_encoder(course))  # Cache for 5 minutes
    return course


@router.put("/{course_id}", response_model=CourseResponse)
def update_course(course_id: int, updated_course: CourseCreate, db: Session = Depends(get_db)):
    """
    Update course information
    """
    course_query = db.query(Course).filter(Course.id == course_id)
    course = course_query.first()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found"
        )

    course_query.update(updated_course.dict(), synchronize_session=False)
    db.commit()
    return course_query.first()


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: int, db: Session = Depends(get_db)):
    """
    Delete a course
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found"
        )

    try:
        db.delete(course)
        db.commit()
        # Invalidate relevant cache entries
        redis_client.delete(f"courses:{course_id}")
        redis_client.delete("courses:all")
        return {"message": "Course deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete course"
        )
@router.post("/{course_id}/bookings", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def book_course(
    course_id: int, 
    booking: CourseBookingCreate, 
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Book a course with concurrency control
    """
    # Check course availability with optimistic locking
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found"
        )
        
    # Check booking deadline
    if course.booking_deadline and datetime.utcnow() > course.booking_deadline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking deadline has passed"
        )
        
    # Check minimum booking hours
    min_booking_time = course.start_time - timedelta(hours=course.min_booking_hours)
    if datetime.utcnow() > min_booking_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Must book at least {course.min_booking_hours} hours before course starts"
        )
    
    # Check member exists
    member = db.query(Member).filter(Member.id == booking.member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member with id {booking.member_id} not found"
        )
    
    # Check if already booked
    existing_booking = db.query(MemberCourseBooking).filter(
        MemberCourseBooking.course_id == course_id,
        MemberCourseBooking.member_id == booking.member_id
    ).first()
    if existing_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Member has already booked this course"
        )
    
    # Check course capacity with optimistic concurrency control
    if course.current_bookings >= course.max_capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course is fully booked"
        )
        
    # Verify course version hasn't changed
    if booking.version is not None and course.version != booking.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Course has been modified by another user"
        )
    
    try:
        # Create booking
        new_booking = MemberCourseBooking(
            course_id=course_id,
            member_id=booking.member_id,
            booking_time=datetime.utcnow()
        )
        db.add(new_booking)
        
        # Update course bookings count
        course.current_bookings += 1
        db.add(course)
        
        db.commit()
        db.refresh(course)
        return course
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to book course"
        )

@router.delete("/{course_id}/bookings/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_booking(
    course_id: int, 
    member_id: int, 
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Cancel a course booking
    """
    # Check booking exists
    booking = db.query(MemberCourseBooking).filter(
        MemberCourseBooking.course_id == course_id,
        MemberCourseBooking.member_id == member_id
    ).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Get course
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found"
        )
    
    try:
        # Delete booking
        db.delete(booking)
        
        # Update course bookings count
        course.current_bookings -= 1
        db.add(course)
        
        db.commit()
        return {"message": "Booking cancelled successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel booking"
        )


# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    try:
        # Create booking
        new_booking = MemberCourseBooking(
            course_id=course_id,
            member_id=booking.member_id,
            booking_time=datetime.utcnow()
        )
        db.add(new_booking)

        # Update course bookings count
        course.current_bookings += 1
        db.add(course)

        db.commit()
        db.refresh(course)
        return course
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to book course"
        )

# [AUTO-APPENDED] Failed to replace, adding new code:
    try:
        # Delete booking
        db.delete(booking)

        # Update course bookings count
        course.current_bookings -= 1
        db.add(course)

        db.commit()
        return {"message": "Booking cancelled successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel booking"
        )