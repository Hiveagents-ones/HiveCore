from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.booking import BookingCreate, BookingResponse, BookingUpdate
from app.services.booking_service import BookingService

router = APIRouter()

@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking: BookingCreate,
    db: Session = Depends(get_db)
):
    """创建新的课程预约"""
    service = BookingService(db)
    return service.create_booking(booking)

@router.get("/", response_model=List[BookingResponse])
def list_bookings(
    skip: int = 0,
    limit: int = 100,
    member_id: Optional[int] = None,
    course_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取预约列表"""
    service = BookingService(db)
    return service.get_bookings(skip=skip, limit=limit, member_id=member_id, course_id=course_id)

@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db)
):
    """获取单个预约详情"""
    service = BookingService(db)
    booking = service.get_booking(booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预约不存在"
        )
    return booking

@router.put("/{booking_id}", response_model=BookingResponse)
def update_booking(
    booking_id: int,
    booking_update: BookingUpdate,
    db: Session = Depends(get_db)
):
    """更新预约信息"""
    service = BookingService(db)
    booking = service.update_booking(booking_id, booking_update)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预约不存在"
        )
    return booking

@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking(
    booking_id: int,
    db: Session = Depends(get_db)
):
    """取消预约"""
    service = BookingService(db)
    success = service.delete_booking(booking_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预约不存在"
        )
    return None

@router.post("/{booking_id}/confirm", response_model=BookingResponse)
def confirm_booking(
    booking_id: int,
    db: Session = Depends(get_db)
):
    """确认预约"""
    service = BookingService(db)
    booking = service.confirm_booking(booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预约不存在或无法确认"
        )
    return booking

@router.post("/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db)
):
    """取消预约"""
    service = BookingService(db)
    booking = service.cancel_booking(booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预约不存在或无法取消"
        )
    return booking