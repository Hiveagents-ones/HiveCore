from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import redis
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
from ....core.auth import get_current_user
from ....models.user import User

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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建新的预约"""
    # 检查用户权限
    if booking.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create booking for this user"
        )
    
    # 并发控制 - 使用Redis锁
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    lock_key = f"booking_lock:{booking.class_schedule_id}"
    
    # 尝试获取锁，最多等待5秒
    if not redis_client.set(lock_key, "locked", nx=True, ex=5):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another booking is in progress for this class"
        )
    
    try:
        # 检查课程容量
        existing_bookings = get_bookings(
            db=db,
            class_schedule_id=booking.class_schedule_id,
            status=BookingStatus.CONFIRMED
        )
        
        # 这里需要从课程表获取最大容量，简化处理假设为20
        max_capacity = 20
        if len(existing_bookings) >= max_capacity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Class is fully booked"
            )
        
        # 检查用户是否已经预约了同一课程
        user_existing = get_bookings(
            db=db,
            user_id=booking.user_id,
            class_schedule_id=booking.class_schedule_id,
            status=BookingStatus.CONFIRMED
        )
        if user_existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already booked this class"
            )
        
        return create_booking(db=db, booking=booking)
    finally:
        # 释放锁
        redis_client.delete(lock_key)


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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新预约状态"""
    # 获取原始预约信息
    original_booking = get_booking(db=db, booking_id=booking_id)
    if original_booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # 检查权限
    if original_booking.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this booking"
        )
    
    # 如果是取消预约，需要检查时间限制（例如：提前2小时取消）
    if booking_update.status == BookingStatus.CANCELLED:
        # 这里需要从课程表获取开始时间，简化处理
        # class_schedule = get_class_schedule(db=db, schedule_id=original_booking.class_schedule_id)
        # if class_schedule.start_time - datetime.now() < timedelta(hours=2):
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail="Cannot cancel booking less than 2 hours before class"
        #     )
        pass
    
    db_booking = update_booking(
        db=db,
        booking_id=booking_id,
        booking_update=booking_update
    )
    return db_booking


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """取消预约"""
    # 获取预约信息
    booking = get_booking(db=db, booking_id=booking_id)
    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # 检查权限
    if booking.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this booking"
        )
    
    # 检查时间限制（例如：提前2小时取消）
    # 这里需要从课程表获取开始时间，简化处理
    # class_schedule = get_class_schedule(db=db, schedule_id=booking.class_schedule_id)
    # if class_schedule.start_time - datetime.now() < timedelta(hours=2):
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Cannot cancel booking less than 2 hours before class"
    #     )
    
    success = delete_booking(db=db, booking_id=booking_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    return None
