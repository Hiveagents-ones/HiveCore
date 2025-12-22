from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import get_current_active_user
from ..core.database import get_db
from ..core.logging import logger
from ..core.rate_limit import rate_limiter
from ..models.course import Course, CourseBooking
from ..schemas.course import CourseCreate, CourseResponse, CourseUpdate, BookingCreate, BookingResponse

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("/", response_model=List[CourseResponse])
@rate_limiter(limit=100, window=60)
async def list_courses(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_active_user)
):
    """
    获取所有可用课程列表
    """
    logger.info(f"User {current_user} requesting course list")
    
    result = await db.execute(
        select(Course)
        .where(Course.is_active == True)
        .offset(skip)
        .limit(limit)
    )
    courses = result.scalars().all()
    
    logger.info(f"Returned {len(courses)} courses to user {current_user}")
    return courses


@router.get("/{course_id}", response_model=CourseResponse)
@rate_limiter(limit=100, window=60)
async def get_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_active_user)
):
    """
    获取特定课程详情
    """
    logger.info(f"User {current_user} requesting course {course_id}")
    
    result = await db.execute(
        select(Course)
        .where(Course.id == course_id, Course.is_active == True)
    )
    course = result.scalar_one_or_none()
    
    if not course:
        logger.warning(f"Course {course_id} not found for user {current_user}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    return course


@router.post("/{course_id}/book", response_model=BookingResponse)
@rate_limiter(limit=10, window=60)
async def book_course(
    course_id: int,
    booking: BookingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_active_user)
):
    """
    预约课程
    """
    logger.info(f"User {current_user} attempting to book course {course_id}")
    
    # 检查课程是否存在且可用
    course_result = await db.execute(
        select(Course)
        .where(Course.id == course_id, Course.is_active == True)
    )
    course = course_result.scalar_one_or_none()
    
    if not course:
        logger.warning(f"Course {course_id} not found for booking by user {current_user}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # 检查是否还有名额
    if course.available_slots <= 0:
        logger.warning(f"No available slots for course {course_id} for user {current_user}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No available slots for this course"
        )
    
    # 检查用户是否已经预约过
    existing_booking = await db.execute(
        select(CourseBooking)
        .where(
            CourseBooking.course_id == course_id,
            CourseBooking.user_id == current_user,
            CourseBooking.status == "active"
        )
    )
    if existing_booking.scalar_one_or_none():
        logger.warning(f"User {current_user} already booked course {course_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already booked this course"
        )
    
    # 创建预约
    new_booking = CourseBooking(
        course_id=course_id,
        user_id=current_user,
        booking_time=datetime.utcnow(),
        status="active"
    )
    
    db.add(new_booking)
    
    # 更新课程可用名额
    course.available_slots -= 1
    
    await db.commit()
    await db.refresh(new_booking)
    
    logger.info(f"User {current_user} successfully booked course {course_id}")
    return new_booking


@router.delete("/{course_id}/book", response_model=dict)
@rate_limiter(limit=10, window=60)
async def cancel_booking(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_active_user)
):
    """
    取消课程预约
    """
    logger.info(f"User {current_user} attempting to cancel booking for course {course_id}")
    
    # 查找预约记录
    booking_result = await db.execute(
        select(CourseBooking)
        .where(
            CourseBooking.course_id == course_id,
            CourseBooking.user_id == current_user,
            CourseBooking.status == "active"
        )
    )
    booking = booking_result.scalar_one_or_none()
    
    if not booking:
        logger.warning(f"No active booking found for course {course_id} by user {current_user}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active booking found for this course"
        )
    
    # 更新预约状态
    booking.status = "cancelled"
    booking.cancellation_time = datetime.utcnow()
    
    # 增加课程可用名额
    course_result = await db.execute(
        select(Course)
        .where(Course.id == course_id)
    )
    course = course_result.scalar_one()
    course.available_slots += 1
    
    await db.commit()
    
    logger.info(f"User {current_user} successfully cancelled booking for course {course_id}")
    return {"message": "Booking cancelled successfully"}


@router.get("/my/bookings", response_model=List[BookingResponse])
@rate_limiter(limit=100, window=60)
async def get_my_bookings(
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_active_user)
):
    """
    获取当前用户的所有预约
    """
    logger.info(f"User {current_user} requesting their bookings")
    
    result = await db.execute(
        select(CourseBooking)
        .where(CourseBooking.user_id == current_user)
        .order_by(CourseBooking.booking_time.desc())
    )
    bookings = result.scalars().all()
    
    logger.info(f"Returned {len(bookings)} bookings to user {current_user}")
    return bookings