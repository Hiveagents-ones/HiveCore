import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[schemas.CourseResponse])
def list_courses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    获取课程列表
    - **skip**: 跳过的记录数
    - **limit**: 返回的最大记录数
    """
    courses = db.query(models.Course).offset(skip).limit(limit).all()
    return courses


@router.post("/book", status_code=status.HTTP_201_CREATED)
def book_course(booking: schemas.CourseBooking, db: Session = Depends(get_db)):
    """
    为会员预约课程
    - **member_id**: 会员的唯一ID
    - **course_id**: 课程的唯一ID
    """
    logger.info(f"Attempting to book course {booking.course_id} for member {booking.member_id}.")
    
    # 检查会员是否存在
    db_member = db.query(models.Member).filter(models.Member.id == booking.member_id).first()
    if not db_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会员不存在"
        )
        
    # 检查课程是否存在
    db_course = db.query(models.Course).filter(models.Course.id == booking.course_id).first()
    if not db_course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在"
        )
    
    # 检查是否已经预约过
    existing_booking = db.query(models.BookingRecord).filter(
        models.BookingRecord.member_id == booking.member_id,
        models.BookingRecord.course_id == booking.course_id
    ).first()
    if existing_booking:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已经预约过此课程"
        )
    # TODO: 检查课程是否已满

    # 创建预约记录
    try:
        db_booking = models.BookingRecord(member_id=booking.member_id, course_id=booking.course_id)
        db.add(db_booking)
        db.commit()
        logger.info(f"Member {booking.member_id} successfully booked course {booking.course_id}.")
        return {"detail": "预约成功"}
    except Exception as e:
        db.rollback()
        logger.error(f"An error occurred during course booking: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="预约失败，请稍后再试"
        )
