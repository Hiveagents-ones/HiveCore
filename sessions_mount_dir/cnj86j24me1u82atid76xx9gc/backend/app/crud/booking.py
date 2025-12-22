from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional
from ..models.booking import Booking, BookingStatus
from ..schemas.booking import BookingCreate, BookingUpdate
from ..models.class_schedule import ClassSchedule
from fastapi import HTTPException, status

def get_booking(db: Session, booking_id: int) -> Optional[Booking]:
    """获取单个预约记录"""
    return db.query(Booking).filter(Booking.id == booking_id).first()

def get_bookings(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    user_id: Optional[int] = None,
    class_schedule_id: Optional[int] = None,
    status: Optional[BookingStatus] = None
) -> List[Booking]:
    """获取预约列表，支持过滤"""
    query = db.query(Booking)
    
    if user_id is not None:
        query = query.filter(Booking.user_id == user_id)
    if class_schedule_id is not None:
        query = query.filter(Booking.class_schedule_id == class_schedule_id)
    if status is not None:
        query = query.filter(Booking.status == status)
    
    return query.offset(skip).limit(limit).all()

def create_booking(db: Session, booking: BookingCreate) -> Booking:
    """创建预约，包含容量检查和并发控制"""
    # 检查课程是否存在
    class_schedule = db.query(ClassSchedule).filter(
        ClassSchedule.id == booking.class_schedule_id
    ).first()
    
    if not class_schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class schedule not found"
        )
    
    # 检查用户是否已经预约了该课程
    existing_booking = db.query(Booking).filter(
        and_(
            Booking.user_id == booking.user_id,
            Booking.class_schedule_id == booking.class_schedule_id,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
        )
    ).first()
    
    if existing_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has already booked this class"
        )
    
    # 使用SELECT FOR UPDATE进行并发控制
    db.execute("BEGIN")
    try:
        # 锁定课程记录
        locked_schedule = db.query(ClassSchedule).with_for_update().filter(
            ClassSchedule.id == booking.class_schedule_id
        ).first()
        
        if not locked_schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Class schedule not found"
            )
        
        # 检查课程容量
        current_bookings = db.query(func.count(Booking.id)).filter(
            and_(
                Booking.class_schedule_id == booking.class_schedule_id,
                Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
            )
        ).scalar()
        
        if current_bookings >= locked_schedule.capacity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Class is fully booked"
            )
        
        # 创建预约
        db_booking = Booking(
            user_id=booking.user_id,
            class_schedule_id=booking.class_schedule_id,
            status=BookingStatus.CONFIRMED  # 直接确认为预约成功
        )
        
        db.add(db_booking)
        db.commit()
        db.refresh(db_booking)
        return db_booking
        
    except Exception as e:
        db.rollback()
        raise e

def update_booking(
    db: Session, 
    booking_id: int, 
    booking_update: BookingUpdate
) -> Optional[Booking]:
    """更新预约状态"""
    db_booking = get_booking(db, booking_id)
    if not db_booking:
        return None
    
    update_data = booking_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_booking, field, value)
    
    db.commit()
    db.refresh(db_booking)
    return db_booking

def cancel_booking(db: Session, booking_id: int) -> Optional[Booking]:
    """取消预约"""
    db_booking = get_booking(db, booking_id)
    if not db_booking:
        return None
    
    if db_booking.status in [BookingStatus.CANCELLED, BookingStatus.COMPLETED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a cancelled or completed booking"
        )
    
    db_booking.status = BookingStatus.CANCELLED
    db.commit()
    db.refresh(db_booking)
    return db_booking

def delete_booking(db: Session, booking_id: int) -> bool:
    """删除预约记录（软删除通过状态更新实现）"""
    db_booking = get_booking(db, booking_id)
    if not db_booking:
        return False
    
    db.delete(db_booking)
    db.commit()
    return True

def get_booking_count_by_schedule(
    db: Session, 
    class_schedule_id: int
) -> int:
    """获取特定课程的预约数量"""
    return db.query(func.count(Booking.id)).filter(
        and_(
            Booking.class_schedule_id == class_schedule_id,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
        )
    ).scalar()

def get_user_bookings(
    db: Session, 
    user_id: int,
    skip: int = 0, 
    limit: int = 100
) -> List[Booking]:
    """获取用户的所有预约"""
    return db.query(Booking).filter(
        Booking.user_id == user_id
    ).offset(skip).limit(limit).all()