from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..services.booking_service import BookingService
from ..models import Booking
from ..core.security import get_current_user
from ..core.monitoring import log_booking_attempt
from ..dependencies import get_db, get_redis

router = APIRouter(prefix="/bookings", tags=["bookings"])

@router.post("/", response_model=dict)
def create_booking(
    course_id: int,
    booking_time: datetime,
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis),
    current_user = Depends(get_current_user)
):
    """
    Create a new booking for a course.
    """
    booking_service = BookingService(db, redis_client)
    
    # Log booking attempt for monitoring
    log_booking_attempt(current_user.id, course_id)
    
    try:
        booking = booking_service.create_booking(
            user_id=current_user.id,
            course_id=course_id,
            booking_time=booking_time
        )
        return {
            "message": "Booking created successfully",
            "booking_id": booking.id,
            "course_id": booking.course_id,
            "user_id": booking.user_id,
            "booking_time": booking.booking_time.isoformat()
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the booking"
        )

@router.get("/", response_model=List[dict])
def get_user_bookings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all bookings for the current user.
    """
    bookings = db.query(Booking).filter(Booking.user_id == current_user.id).all()
    return [
        {
            "id": booking.id,
            "course_id": booking.course_id,
            "booking_time": booking.booking_time.isoformat(),
            "status": booking.status
        }
        for booking in bookings
    ]

@router.get("/{booking_id}", response_model=dict)
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get a specific booking by ID.
    """
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.user_id == current_user.id
    ).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    return {
        "id": booking.id,
        "course_id": booking.course_id,
        "booking_time": booking.booking_time.isoformat(),
        "status": booking.status
    }

@router.delete("/{booking_id}", response_model=dict)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis),
    current_user = Depends(get_current_user)
):
    """
    Cancel a booking.
    """
    booking_service = BookingService(db, redis_client)
    
    try:
        success = booking_service.cancel_booking(booking_id, current_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found or cannot be cancelled"
            )
        return {"message": "Booking cancelled successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while cancelling the booking"
        )
