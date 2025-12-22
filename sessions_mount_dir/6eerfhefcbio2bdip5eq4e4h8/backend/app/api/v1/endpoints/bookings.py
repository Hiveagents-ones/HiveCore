from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .... import crud, schemas
from ....database import get_db


router = APIRouter()


@router.post("/", response_model=schemas.Booking, status_code=status.HTTP_201_CREATED)
def create_booking(booking: schemas.BookingCreate, db: Session = Depends(get_db)):
    """
    Create a new booking.
    """
    # In a real application, you would get the member_id from the authenticated user.
    # For this example, we'll assume a member_id of 1.
    # TODO: Replace with actual member_id from JWT token or session.
    member_id = 1

    # Check if the course exists
    db_course = crud.get_course(db, course_id=booking.course_id)
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if the course is active
    if not db_course.is_active:
        raise HTTPException(status_code=400, detail="Cannot book an inactive course")

    # Check if the course has reached its capacity
    current_bookings = crud.get_bookings_by_course(db, course_id=booking.course_id)
    if len(current_bookings) >= db_course.capacity:
        raise HTTPException(status_code=400, detail="Course is fully booked")
    
    # Check if the member has already booked this course
    existing_booking = crud.get_booking_by_member_and_course(db, member_id=member_id, course_id=booking.course_id)
    if existing_booking:
        raise HTTPException(status_code=400, detail="Member has already booked this course")

    return crud.create_booking(db=db, booking=booking, member_id=member_id)


@router.get("/", response_model=List[schemas.Booking])
def read_bookings(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve all bookings.
    """
    bookings = crud.get_bookings(db, skip=skip, limit=limit)
    return bookings


@router.get("/member/{member_id}", response_model=List[schemas.Booking])
def read_bookings_by_member(member_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve all bookings for a specific member.
    """
    bookings = crud.get_bookings_by_member(db, member_id=member_id, skip=skip, limit=limit)
    return bookings


@router.get("/course/{course_id}", response_model=List[schemas.Booking])
def read_bookings_by_course(course_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve all bookings for a specific course.
    """
    # Check if the course exists
    db_course = crud.get_course(db, course_id=course_id)
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    bookings = crud.get_bookings_by_course(db, course_id=course_id, skip=skip, limit=limit)
    return bookings


@router.get("/{booking_id}", response_model=schemas.Booking)
def read_booking(booking_id: int, db: Session = Depends(get_db)):
    """
    Get a specific booking by ID.
    """
    db_booking = crud.get_booking(db, booking_id=booking_id)
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return db_booking


@router.put("/{booking_id}", response_model=schemas.Booking)
def update_booking(booking_id: int, booking: schemas.BookingUpdate, db: Session = Depends(get_db)):
    """
    Update a booking.
    """
    db_booking = crud.get_booking(db, booking_id=booking_id)
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return crud.update_booking(db=db, booking_id=booking_id, booking=booking)


@router.delete("/{booking_id}", response_model=schemas.Booking)
def delete_booking(booking_id: int, db: Session = Depends(get_db)):
    """
    Delete a booking.
    """
    db_booking = crud.get_booking(db, booking_id=booking_id)
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return crud.delete_booking(db=db, booking_id=booking_id)
