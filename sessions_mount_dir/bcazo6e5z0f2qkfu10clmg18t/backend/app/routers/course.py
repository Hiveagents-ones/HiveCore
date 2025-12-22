from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import models, schemas
from ..database import get_db
from ..dependencies import get_current_user

router = APIRouter(
    prefix="/courses",
    tags=["courses"]
)


@router.get("/", response_model=schemas.CourseList)
def list_courses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    获取课程列表，支持分页和按类别筛选
    """
    query = db.query(models.Course).filter(models.Course.is_active == True)
    
    if category:
        query = query.filter(models.Course.category == category)
    
    total = query.count()
    courses = query.offset(skip).limit(limit).all()
    
    return schemas.CourseList(courses=courses, total=total)


@router.get("/{course_id}", response_model=schemas.Course)
def get_course(course_id: int, db: Session = Depends(get_db)):
    """
    获取单个课程详情
    """
    course = db.query(models.Course).filter(
        models.Course.id == course_id,
        models.Course.is_active == True
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在"
        )
    
    return course


@router.post("/{course_id}/book", response_model=schemas.Booking)
def book_course(
    course_id: int,
    booking: schemas.BookingCreate = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    预约课程
    """
    # 检查课程是否存在
    course = db.query(models.Course).filter(
        models.Course.id == course_id,
        models.Course.is_active == True
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在"
        )
    
    # 检查用户是否是会员
    if not current_user.is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有会员才能预约课程"
        )
    
    # 检查课程是否已满
    if course.is_full:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="课程已满"
        )
    
    # 检查用户是否已经预约过该课程
    existing_booking = db.query(models.Booking).filter(
        models.Booking.user_id == current_user.id,
        models.Booking.course_id == course_id,
        models.Booking.status == "confirmed"
    ).first()
    
    if existing_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已经预约过该课程"
        )
    
    # 创建预约
    booking_data = {
        "user_id": current_user.id,
        "course_id": course_id,
        "status": "confirmed",
        "notes": booking.notes if booking else None
    }
    
    db_booking = models.Booking(**booking_data)
    db.add(db_booking)
    
    # 更新课程预约数
    course.current_bookings += 1
    
    # 创建通知
    notification = models.Notification(
        user_id=current_user.id,
        title="课程预约成功",
        message=f"您已成功预约课程 {course.name}，时间：{course.start_time}，地点：{course.location}",
        type="booking"
    )
    db.add(notification)
    
    db.commit()
    db.refresh(db_booking)
    
    # 加载关联数据
    db_booking.user = current_user
    db_booking.course = course
    
    return db_booking


@router.delete("/{course_id}/book", response_model=schemas.Booking)
def cancel_booking(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    取消预约
    """
    # 查找预约记录
    booking = db.query(models.Booking).filter(
        models.Booking.user_id == current_user.id,
        models.Booking.course_id == course_id,
        models.Booking.status == "confirmed"
    ).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到预约记录"
        )
    
    # 更新预约状态
    booking.status = "cancelled"
    
    # 更新课程预约数
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if course:
        course.current_bookings = max(0, course.current_bookings - 1)
    
    # 创建通知
    notification = models.Notification(
        user_id=current_user.id,
        title="课程预约已取消",
        message=f"您已取消课程 {course.name} 的预约",
        type="booking"
    )
    db.add(notification)
    
    db.commit()
    db.refresh(booking)
    
    # 加载关联数据
    booking.user = current_user
    booking.course = course
    
    return booking


@router.get("/{course_id}/bookings", response_model=schemas.BookingList)
def get_course_bookings(
    course_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    获取课程的预约列表（仅管理员）
    """
    # TODO: 添加管理员权限检查
    
    query = db.query(models.Booking).filter(
        models.Booking.course_id == course_id,
        models.Booking.status == "confirmed"
    )
    
    total = query.count()
    bookings = query.offset(skip).limit(limit).all()
    
    return schemas.BookingList(bookings=bookings, total=total)


@router.get("/categories/list", response_model=List[str])
def get_course_categories(db: Session = Depends(get_db)):
    """
    获取所有课程类别
    """
    categories = db.query(models.Course.category).distinct().all()
    return [c[0] for c in categories if c[0]]