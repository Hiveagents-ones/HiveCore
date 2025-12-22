from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import BackgroundTasks
from fastapi import Query
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import CourseBooking, Member, CourseSchedule
from ..models import BookingAuditLog
from ..schemas import CourseBookingResponse, CourseBookingCreate

router = APIRouter(
logger = logging.getLogger(__name__)
    prefix="/api/v1/bookings",
    tags=["bookings"]
)

@router.get("/", response_model=List[CourseBookingResponse])
def get_all_bookings(
    skip: int = Query(0, ge=0, description="分页偏移量"),
    limit: int = Query(100, le=200, description="每页记录数"),
    db: Session = Depends(get_db)
):
    """获取所有预约记录"""
    bookings = db.query(CourseBooking).offset(skip).limit(limit).all()
    if not bookings:
        raise HTTPException(status_code=404, detail="No bookings found")
    return bookings

@router.get("/member/{member_id}", response_model=List[CourseBookingResponse])
def get_member_bookings(member_id: int, db: Session = Depends(get_db)):
    """获取会员的预约记录"""
    # 检查会员是否存在
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    bookings = db.query(CourseBooking).filter(CourseBooking.member_id == member_id).all()
    if not bookings:
        raise HTTPException(status_code=404, detail="No bookings found for this member")
    return bookings

@router.post("/", response_model=CourseBookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    # 检查课程容量
    booked_count = db.query(CourseBooking).filter(
        CourseBooking.schedule_id == booking.schedule_id
    ).count()
    
    schedule = db.query(CourseSchedule).filter(CourseSchedule.id == booking.schedule_id).first()
    if booked_count >= schedule.capacity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Course is fully booked"
        )
    booking: CourseBookingCreate, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """创建新的课程预约"""
    # 检查会员是否存在
    member = db.query(Member).filter(Member.id == booking.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # 检查课程安排是否存在
    schedule = db.query(CourseSchedule).filter(CourseSchedule.id == booking.schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Course schedule not found")

    # 检查是否已预约
    existing_booking = db.query(CourseBooking).filter(
        CourseBooking.member_id == booking.member_id,
        CourseBooking.schedule_id == booking.schedule_id
    ).first()

    if existing_booking:
        raise HTTPException(status_code=400, detail="Already booked this course")

    # 检查预约时间是否有效
    if schedule.start_time < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot book past courses"
        )
        
    # 检查课程容量
    booked_count = db.query(CourseBooking).filter(
        CourseBooking.schedule_id == booking.schedule_id
    ).count()
    if booked_count >= schedule.capacity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Course is fully booked"
        )
    db_booking = CourseBooking(**booking.dict())
    background_tasks.add_task(log_booking_activity, "created", booking.member_id, booking.schedule_id, db_booking.id)
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking

@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_booking(
    booking_id: int, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """取消课程预约"""
    booking = db.query(CourseBooking).filter(CourseBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    db.delete(booking)
    background_tasks.add_task(log_booking_activity, "cancelled", booking.member_id, booking.schedule_id, booking.id)
    db.commit()
    return {"message": "Booking cancelled successfully"}

def log_booking_activity(
    action: str, 
    member_id: int, 
    schedule_id: int, 
    booking_id: int,
    db: Session = Depends(get_db)
):
    """记录预约活动日志"""
    # 记录到数据库审计表
    audit_log = BookingAuditLog(
        action=action,
        member_id=member_id,
        schedule_id=schedule_id,
        booking_id=booking_id,
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)
    db.commit()
    
    # 记录到日志系统
    logger.info(
        f"Booking {action} - "
        f"member_id: {member_id}, "
        f"schedule_id: {schedule_id}, "
        f"booking_id: {booking_id}, "
        f"timestamp: {datetime.utcnow()}"
    )