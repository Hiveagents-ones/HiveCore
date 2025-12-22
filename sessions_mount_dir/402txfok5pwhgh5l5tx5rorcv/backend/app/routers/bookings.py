from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Booking, Course, Member
from ..schemas import BookingCreate, BookingResponse
from ..middleware.audit import AuditMiddleware
import json

router = APIRouter(prefix="/api/v1/courses/{course_id}/bookings", tags=["bookings"])

@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(course_id: int, booking: BookingCreate, request: Request, db: Session = Depends(get_db)):
    # Check if course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if member exists
    member = db.query(Member).filter(Member.id == booking.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Check if member already booked this course
    existing_booking = db.query(Booking).filter(
        Booking.member_id == booking.member_id,
        Booking.course_id == course_id
    ).first()
    if existing_booking:
        raise HTTPException(status_code=400, detail="Member already booked this course")
    
    # Check course capacity
    current_bookings = db.query(Booking).filter(
        Booking.course_id == course_id,
        Booking.status == "confirmed"
    ).count()
    if current_bookings >= course.capacity:
        raise HTTPException(status_code=400, detail="Course is fully booked")
    
    # Create booking
    db_booking = Booking(
        member_id=booking.member_id,
        course_id=course_id,
        status="confirmed"
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    
    return db_booking

@router.get("/", response_model=List[BookingResponse])
def get_bookings(course_id: int, db: Session = Depends(get_db)):
    # Check if course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    bookings = db.query(Booking).filter(Booking.course_id == course_id).all()
    return bookings

@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_booking(course_id: int, booking_id: int, request: Request, db: Session = Depends(get_db)):
    # Check if course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Get booking
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.course_id == course_id
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Cancel booking
    booking.status = "cancelled"
    db.commit()
    
    return None

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    # Create booking
    db_booking = Booking(
        member_id=booking.member_id,
        course_id=course_id,
        status="confirmed"
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)

    # Log audit
    audit_data = {
        "action": "create_booking",
        "course_id": course_id,
        "member_id": booking.member_id,
        "booking_id": db_booking.id,
        "timestamp": datetime.utcnow().isoformat()
    }
    await AuditMiddleware.log_audit(request, audit_data)

    return db_booking

# [AUTO-APPENDED] Failed to replace, adding new code:
    # Cancel booking
    booking.status = "cancelled"
    db.commit()

    # Log audit
    audit_data = {
        "action": "cancel_booking",
        "course_id": course_id,
        "member_id": booking.member_id,
        "booking_id": booking.id,
        "timestamp": datetime.utcnow().isoformat()
    }
    await AuditMiddleware.log_audit(request, audit_data)

    return None