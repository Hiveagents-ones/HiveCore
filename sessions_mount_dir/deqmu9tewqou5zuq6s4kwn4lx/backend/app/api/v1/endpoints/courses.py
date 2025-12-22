from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.api.deps import get_current_user, get_db
from app.models import Course, Booking, User
from app.schemas.course import Course as CourseSchema, CourseCreate, CourseUpdate
from app.schemas.booking import Booking as BookingSchema

router = APIRouter()

@router.get("/", response_model=List[CourseSchema])
def list_courses(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None),
    instructor: Optional[str] = Query(None),
    start_time_from: Optional[datetime] = Query(None),
    start_time_to: Optional[datetime] = Query(None),
    is_active: Optional[bool] = Query(True)
):
    """
    获取课程列表，支持搜索和筛选
    """
    query = db.query(Course)
    
    # 基础筛选
    if is_active is not None:
        query = query.filter(Course.is_active == is_active)
    
    # 搜索课程名称或描述
    if search:
        query = query.filter(
            or_(
                Course.name.ilike(f"%{search}%"),
                Course.description.ilike(f"%{search}%")
            )
        )
    
    # 按教练筛选
    if instructor:
        query = query.filter(Course.instructor.ilike(f"%{instructor}%"))
    
    # 按时间范围筛选
    if start_time_from:
        query = query.filter(Course.start_time >= start_time_from)
    if start_time_to:
        query = query.filter(Course.start_time <= start_time_to)
    
    # 分页
    courses = query.offset(skip).limit(limit).all()
    
    # 计算剩余名额
    for course in courses:
        course.remaining_slots = course.max_capacity - course.current_bookings
    
    return courses

@router.get("/{course_id}", response_model=CourseSchema)
def get_course(
    course_id: int,
    db: Session = Depends(get_db)
):
    """
    获取单个课程详情
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    course.remaining_slots = course.max_capacity - course.current_bookings
    return course

@router.post("/", response_model=CourseSchema)
def create_course(
    course: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建新课程（需要管理员权限）
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db_course = Course(**course.dict())
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    
    db_course.remaining_slots = db_course.max_capacity - db_course.current_bookings
    return db_course

@router.put("/{course_id}", response_model=CourseSchema)
def update_course(
    course_id: int,
    course_update: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新课程信息（需要管理员权限）
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    update_data = course_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_course, field, value)
    
    db_course.version += 1  # 乐观并发控制
    db.commit()
    db.refresh(db_course)
    
    db_course.remaining_slots = db_course.max_capacity - db_course.current_bookings
    return db_course

@router.delete("/{course_id}")
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除课程（需要管理员权限）
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # 检查是否有预约
    active_bookings = db.query(Booking).filter(
        and_(
            Booking.course_id == course_id,
            Booking.is_cancelled == False
        )
    ).count()
    
    if active_bookings > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete course with active bookings"
        )
    
    db.delete(db_course)
    db.commit()
    return {"message": "Course deleted successfully"}

@router.get("/{course_id}/bookings", response_model=List[BookingSchema])
def get_course_bookings(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取课程的所有预约（需要管理员权限或课程教练权限）
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if not (current_user.is_superuser or current_user.username == course.instructor):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    bookings = db.query(Booking).filter(
        and_(
            Booking.course_id == course_id,
            Booking.is_cancelled == False
        )
    ).all()
    
    return bookings

@router.get("/{course_id}/availability")
def check_course_availability(
    course_id: int,
    db: Session = Depends(get_db)
):
    """
    检查课程可用性（剩余名额）
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    remaining_slots = course.max_capacity - course.current_bookings
    return {
        "course_id": course_id,
        "course_name": course.name,
        "max_capacity": course.max_capacity,
        "current_bookings": course.current_bookings,
        "remaining_slots": remaining_slots,
        "is_available": remaining_slots > 0 and course.is_active
    }
