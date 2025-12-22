from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
import redis
import json
from fastapi import HTTPException, status
from ..models import Booking, Course, User
from ..core.security import get_current_user
from ..core.monitoring import log_booking_attempt

class BookingService:
    def __init__(self, db: Session, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client
        self.lock_timeout = 30  # seconds
        
    def _get_lock_key(self, course_id: int) -> str:
        return f"booking_lock:course_{course_id}"
    
    def _get_inventory_key(self, course_id: int) -> str:
        return f"course_inventory:{course_id}"
    
    def _acquire_lock(self, course_id: int) -> bool:
        lock_key = self._get_lock_key(course_id)
        return self.redis.set(lock_key, "locked", nx=True, ex=self.lock_timeout)
    
    def _release_lock(self, course_id: int):
        lock_key = self._get_lock_key(course_id)
        self.redis.delete(lock_key)
    
    def _initialize_inventory(self, course: Course):
        inventory_key = self._get_inventory_key(course.id)
        if not self.redis.exists(inventory_key):
            self.redis.set(inventory_key, course.max_participants)
    
    def _check_availability(self, course_id: int) -> bool:
        inventory_key = self._get_inventory_key(course_id)
        remaining = self.redis.get(inventory_key)
        if remaining is None:
            course = self.db.query(Course).filter(Course.id == course_id).first()
            if not course:
                return False
            self._initialize_inventory(course)
            remaining = course.max_participants
        return int(remaining) > 0
    
    def _decrement_inventory(self, course_id: int) -> bool:
        inventory_key = self._get_inventory_key(course_id)
        return self.redis.decr(inventory_key) >= 0
    
    def _increment_inventory(self, course_id: int):
        inventory_key = self._get_inventory_key(course_id)
        self.redis.incr(inventory_key)
    
    def create_booking(self, user_id: int, course_id: int, booking_time: datetime) -> Booking:
        # Check if course exists and is active
        course = self.db.query(Course).filter(
            and_(Course.id == course_id, Course.is_active == True)
        ).first()
        
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found or inactive"
            )
        
        # Acquire distributed lock
        if not self._acquire_lock(course_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many booking requests. Please try again later."
            )
        
        try:
            # Initialize inventory if needed
            self._initialize_inventory(course)
            
            # Check availability
            if not self._check_availability(course_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No available slots for this course"
                )
            
            # Check if user already has a booking for this course
            existing_booking = self.db.query(Booking).filter(
                and_(
                    Booking.user_id == user_id,
                    Booking.course_id == course_id,
                    Booking.status == "confirmed"
                )
            ).first()
            
            if existing_booking:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="You already have a booking for this course"
                )
            
            # Decrement inventory
            if not self._decrement_inventory(course_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Failed to reserve slot. Please try again."
                )
            
            # Create booking
            booking = Booking(
                user_id=user_id,
                course_id=course_id,
                booking_time=booking_time,
                status="confirmed",
                created_at=datetime.utcnow()
            )
            
            self.db.add(booking)
            self.db.commit()
            self.db.refresh(booking)
            
            # Log booking attempt
            log_booking_attempt(user_id, course_id, True)
            
            return booking
            
        except Exception as e:
            # Rollback inventory on failure
            self._increment_inventory(course_id)
            self.db.rollback()
            log_booking_attempt(user_id, course_id, False)
            raise e
        finally:
            # Always release the lock
            self._release_lock(course_id)
    
    def cancel_booking(self, booking_id: int, user_id: int) -> bool:
        booking = self.db.query(Booking).filter(
            and_(Booking.id == booking_id, Booking.user_id == user_id)
        ).first()
        
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        if booking.status != "confirmed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking cannot be cancelled"
            )
        
        # Check cancellation policy (e.g., 24 hours before)
        if booking.booking_time - datetime.utcnow() < timedelta(hours=24):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel booking within 24 hours of the scheduled time"
            )
        
        # Acquire lock
        if not self._acquire_lock(booking.course_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="System busy. Please try again later."
            )
        
        try:
            # Update booking status
            booking.status = "cancelled"
            booking.updated_at = datetime.utcnow()
            
            # Increment inventory
            self._increment_inventory(booking.course_id)
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            raise e
        finally:
            self._release_lock(booking.course_id)
    
    def get_user_bookings(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Booking]:
        return self.db.query(Booking).filter(
            Booking.user_id == user_id
        ).offset(skip).limit(limit).all()
    
    def get_booking_details(self, booking_id: int, user_id: int) -> Optional[Booking]:
        return self.db.query(Booking).filter(
            and_(Booking.id == booking_id, Booking.user_id == user_id)
        ).first()
    
    def get_course_availability(self, course_id: int) -> dict:
        course = self.db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        self._initialize_inventory(course)
        inventory_key = self._get_inventory_key(course_id)
        remaining = int(self.redis.get(inventory_key))
        
        return {
            "course_id": course_id,
            "max_participants": course.max_participants,
            "remaining_slots": remaining,
            "is_available": remaining > 0
        }
