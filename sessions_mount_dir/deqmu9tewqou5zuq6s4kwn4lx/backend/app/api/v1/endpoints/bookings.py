from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.api.deps import get_current_user, get_db
from app.models import User, Course, Booking
from app.schemas import BookingCreate, BookingResponse, BookingCancel

router = APIRouter()


@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new booking for a course.
    """
    # Get the course with lock
    course = db.query(Course).filter(
        and_(
            Course.id == booking.course_id,
            Course.is_active == True
        )
    ).with_for_update().first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or inactive"
        )
    
    # Check if course is full
    if course.current_bookings >= course.max_capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course is fully booked"
        )
    
    # Check if user already has a booking for this course
    existing_booking = db.query(Booking).filter(
        and_(
            Booking.user_id == current_user.id,
            Booking.course_id == booking.course_id,
            Booking.is_cancelled == False
        )
    ).first()
    
    if existing_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an active booking for this course"
        )
    
    # Create new booking
    new_booking = Booking(
        user_id=current_user.id,
        course_id=booking.course_id
    )
    
    # Update course booking count
    course.current_bookings += 1
    course.version += 1
    
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    
    return new_booking


@router.delete("/{booking_id}", response_model=BookingResponse)
def cancel_booking(
    booking_id: int,
    cancel_data: BookingCancel,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel an existing booking.
    """
    # Get the booking with lock
    booking = db.query(Booking).filter(
        and_(
            Booking.id == booking_id,
            Booking.user_id == current_user.id,
            Booking.is_cancelled == False
        )
    ).with_for_update().first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found or already cancelled"
        )
    
    # Get the course with lock
    course = db.query(Course).filter(
        Course.id == booking.course_id
    ).with_for_update().first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated course not found"
        )
    
    # Cancel the booking
    booking.is_cancelled = True
    booking.cancelled_at = datetime.utcnow()
    booking.version += 1
    
    # Update course booking count
    course.current_bookings -= 1
    course.version += 1
    
    db.commit()
    db.refresh(booking)
    
    return booking


@router.get("/", response_model=List[BookingResponse])
def get_user_bookings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Get all bookings for the current user.
    """
    bookings = db.query(Booking).filter(
        Booking.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    return bookings


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific booking by ID.
    """
    booking = db.query(Booking).filter(
        and_(
            Booking.id == booking_id,
            Booking.user_id == current_user.id
        )
    ).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    return booking
