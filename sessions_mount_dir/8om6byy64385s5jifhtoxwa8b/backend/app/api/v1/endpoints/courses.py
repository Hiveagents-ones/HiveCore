from typing import List, Optional
from datetime import datetime, date
from sqlalchemy import select, update, func
from sqlalchemy.orm import with_for_update
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ....database import get_db
from ....schemas.course import Course, CourseCreate, CourseUpdate, Booking, BookingCreate, BookingUpdate, CourseWithBookings
from ....crud.course import CourseCRUD, BookingCRUD
import logging

router = APIRouter()

course_crud = CourseCRUD()
booking_crud = BookingCRUD()

@router.get("/", response_model=List[Course])
def read_courses(
    skip: int = 0,
    limit: int = 100,
    instructor: Optional[str] = None,
    location: Optional[str] = None,
    is_active: Optional[bool] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    include_availability: Optional[bool] = False,
    db: Session = Depends(get_db)
):
    """获取课程列表"""
    try:
        courses = course_crud.get_multi(
            db, skip=skip, limit=limit, instructor=instructor, location=location, is_active=is_active,
            start_date=start_date, end_date=end_date
        )
    except Exception as e:
        logging.error(f"Error fetching courses: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch courses"
        )
    
    if include_availability:
        for course in courses:
            bookings = booking_crud.get_multi_by_course(db, course.id)
            current_bookings = len([b for b in bookings if not b.is_cancelled])
            course.current_bookings = current_bookings
            course.available_spots = max(0, course.capacity - current_bookings)
    
    return courses

@router.post("/", response_model=Course)
def create_course(
    course_in: CourseCreate,
    db: Session = Depends(get_db)
):
    """创建新课程"""
    try:
        course = course_crud.create(db, course_in)
        logging.info(f"Successfully created course: {course.title}")
        return course
    except ValueError as e:
        logging.error(f"Validation error creating course: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logging.error(f"Error creating course: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create course"
        )

@router.get("/{course_id}", response_model=Course)
def read_course(
    course_id: int,
    include_availability: Optional[bool] = False,
    db: Session = Depends(get_db)
):
    """获取单个课程"""
    course = course_crud.get(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    if include_availability:
        bookings = booking_crud.get_multi_by_course(db, course_id)
        current_bookings = len([b for b in bookings if not b.is_cancelled])
        course.current_bookings = current_bookings
        course.available_spots = max(0, course.capacity - current_bookings)
    
    return course

@router.put("/{course_id}", response_model=Course)
def update_course(
    course_id: int,
    course_in: CourseUpdate,
    db: Session = Depends(get_db)
):
    """更新课程"""
    course = course_crud.get(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    try:
        updated_course = course_crud.update(db, course, course_in)
        logging.info(f"Successfully updated course: {updated_course.title}")
        return updated_course
    except ValueError as e:
        logging.error(f"Validation error updating course: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logging.error(f"Error updating course: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update course"
        )

@router.delete("/{course_id}", response_model=Course)
def delete_course(
    course_id: int,
    db: Session = Depends(get_db)
):
    """删除课程"""
    try:
        course = course_crud.delete(db, course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        logging.info(f"Successfully deleted course: {course.title}")
        return course
    except Exception as e:
        logging.error(f"Error deleting course: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete course"
        )

@router.get("/{course_id}/bookings", response_model=List[Booking])
def read_course_bookings(
    course_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取课程预约列表"""
    course = course_crud.get(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    return booking_crud.get_multi_by_course(db, course_id, skip=skip, limit=limit)

@router.post("/{course_id}/bookings", response_model=Booking)
def create_booking(
    course_id: int,
    booking_in: BookingCreate,
    db: Session = Depends(get_db)
):
    """预约课程"""
    course = course_crud.get(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    available_spots = course_crud.get_available_slots(db, course_id)
    if available_spots <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No available spots for this course"
        )
    
    existing_booking = booking_crud.get_by_user_and_course(db, booking_in.user_id, course_id)
    if existing_booking and not existing_booking.is_cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has already booked this course"
        )
    
    booking_in.course_id = course_id
    return booking_crud.create(db, booking_in)

@router.get("/{course_id}/bookings/{booking_id}", response_model=Booking)
def read_booking(
    course_id: int,
    booking_id: int,
    db: Session = Depends(get_db)
):
    """获取单个预约"""
    booking = booking_crud.get(db, booking_id)
    if not booking or booking.course_id != course_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    return booking

@router.put("/{course_id}/bookings/{booking_id}", response_model=Booking)
def update_booking(
    course_id: int,
    booking_id: int,
    booking_in: BookingUpdate,
    db: Session = Depends(get_db)
):
    """更新预约"""
    booking = booking_crud.get(db, booking_id)
    if not booking or booking.course_id != course_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    return booking_crud.update(db, booking, booking_in)

@router.delete("/{course_id}/bookings/{booking_id}", response_model=Booking)
def delete_booking(
    course_id: int,
    booking_id: int,
    db: Session = Depends(get_db)
):
    """取消预约"""
    try:
        with db.begin():
            # 使用 FOR UPDATE 锁定预约记录
            stmt = select(Booking).where(
                Booking.id == booking_id,
                Booking.course_id == course_id
            ).with_for_update()
            booking = db.execute(stmt).scalar_one_or_none()
            
            if not booking:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Booking not found"
                )

            if booking.is_cancelled:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Booking is already cancelled"
                )

            # 检查课程是否已开始
            course_stmt = select(Course).where(Course.id == course_id)
            course = db.execute(course_stmt).scalar_one_or_none()
            
            if course and course.start_time <= datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot cancel a booking for a course that has already started"
                )

            # 软删除预约
            booking.is_cancelled = True
            booking.cancelled_at = datetime.utcnow()
            db.add(booking)
            
            # 更新课程时间戳
            if course:
                course.updated_at = datetime.utcnow()
                db.add(course)
            
            return booking
    except Exception as e:
        db.rollback()
        raise e

@router.get("/{course_id}/details", response_model=CourseWithBookings)
@router.get("/{course_id}/availability")
def get_course_availability(
    course_id: int,
    db: Session = Depends(get_db)
):
    """获取课程容量和预约状态"""
    course = course_crud.get(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    bookings = booking_crud.get_multi_by_course(db, course_id)
    current_bookings = len([b for b in bookings if not b.is_cancelled])
    available_spots = max(0, course.capacity - current_bookings)
    
    # 实时更新课程容量
    course.current_bookings = current_bookings
    course.available_spots = available_spots
    
    return {
        "course_id": course_id,
        "course_name": course.name,
        "capacity": course.capacity,
        "current_bookings": current_bookings,
        "available_spots": available_spots,
        "is_full": available_spots == 0,
        "start_time": course.start_time,
        "end_time": course.end_time,
        "status": "full" if available_spots == 0 else "available",
        "updated_at": datetime.utcnow()
    }


@router.get("/{course_id}/with-bookings", response_model=CourseWithBookings)
def read_course_with_bookings(
    course_id: int,
    db: Session = Depends(get_db)
):
    """获取课程详情（包含预约信息）"""
    course = course_crud.get(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    bookings = booking_crud.get_multi_by_course(db, course_id)
    current_bookings = len([b for b in bookings if not b.is_cancelled])
    available_spots = max(0, course.capacity - current_bookings)
    
    return CourseWithBookings(
        **course.__dict__,
        bookings=bookings,
        current_bookings=current_bookings,
        available_spots=available_spots
    )
