from fastapi import APIRouter, Depends, HTTPException, status
import logging
from contextlib import contextmanager
from fastapi_redis_cache import FastApiRedisCache, cache
from redis import Redis
from redis.exceptions import LockError
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..config import settings
from ..models import Booking, Course, Member
from ..schemas import BookingCreate, BookingResponse

router = APIRouter(
    prefix="/api/v1/bookings",
    tags=["bookings"]
)

logger = logging.getLogger(__name__)

redis_client = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

@contextmanager
def acquire_lock(lock_name, timeout=10):
    """
    Context manager for acquiring and releasing Redis lock
    """
    lock = redis_client.lock(lock_name, timeout=timeout)
    try:
        acquired = lock.acquire(blocking=True)
        if not acquired:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not acquire lock for booking operation"
            )
        yield
    finally:
        try:
            lock.release()
        except LockError:
            logger.warning(f"Failed to release lock {lock_name}")
    prefix="/api/v1/bookings",
    tags=["bookings"]
)


@router.get("/", response_model=List[BookingResponse])
@cache(expire=30)
def get_bookings(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get all bookings with pagination
    """
    logger.info(f"Fetching bookings with skip={skip} and limit={limit}")
    bookings = db.query(Booking).offset(skip).limit(limit).all()
    logger.debug(f"Found {len(bookings)} bookings")
    return bookings


@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(booking: BookingCreate, db: Session = Depends(get_db)):
    """
    Create a new booking with distributed lock
    """
    lock_name = f"booking_lock:{booking.member_id}:{booking.course_id}"
    with acquire_lock(lock_name):
        logger.info(f"Creating booking for member {booking.member_id} on course {booking.course_id}")
    # Check if member exists
    member = db.query(Member).filter(Member.id == booking.member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    # Check if course exists
    course = db.query(Course).filter(Course.id == booking.course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Check if booking already exists
    existing_booking = db.query(Booking).filter(
        Booking.member_id == booking.member_id,
        Booking.course_id == booking.course_id
    ).first()
    
    if existing_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking already exists"
        )

    db_booking = Booking(**booking.dict())
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    """
    Cancel a booking by ID with distributed lock
    """
    lock_name = f"cancel_booking_lock:{booking_id}"
    with acquire_lock(lock_name):
        logger.info(f"Canceling booking with ID {booking_id}")
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    db.delete(booking)
    db.commit()
    return {"message": "Booking cancelled successfully"}