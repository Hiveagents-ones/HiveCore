from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ....database import get_db
from ....schemas.booking import Booking, BookingCreate, BookingUpdate
from ....crud.booking import (
    get_booking,
    get_bookings,
    create_booking,
    update_booking,
    delete_booking
)
from ....models.booking import BookingStatus

router = APIRouter()


@router.post("/", response_model=Booking, status_code=status.HTTP_201_CREATED)
def create_new_booking(
    booking: BookingCreate,
    db: Session = Depends(get_db)
):
    """创建新的预约"""
    return create_booking(db=db, booking=booking)


@router.get("/", response_model=List[Booking])
def read_bookings(
    skip: int = 0,
    limit: int = 100,
    user_id: int = None,
    class_schedule_id: int = None,
    status: BookingStatus = None,
    db: Session = Depends(get_db)
):
    """获取预约列表"""
    bookings = get_bookings(
        db=db,
        skip=skip,
        limit=limit,
        user_id=user_id,
        class_schedule_id=class_schedule_id,
        status=status
    )
    return bookings


@router.get("/{booking_id}", response_model=Booking)
def read_booking(
    booking_id: int,
    db: Session = Depends(get_db)
):
    """获取单个预约详情"""
    db_booking = get_booking(db=db, booking_id=booking_id)
    if db_booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    return db_booking


@router.put("/{booking_id}", response_model=Booking)
def update_existing_booking(
    booking_id: int,
    booking_update: BookingUpdate,
    db: Session = Depends(get_db)
):
    """更新预约状态"""
    db_booking = update_booking(
        db=db,
        booking_id=booking_id,
        booking_update=booking_update
    )
    if db_booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    return db_booking


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_booking(
    booking_id: int,
    db: Session = Depends(get_db)
):
    """取消预约"""
    success = delete_booking(db=db, booking_id=booking_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
    )
    return None
