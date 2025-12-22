from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import database, schemas, models
from ..middleware.auth import get_current_member, Permission, CoursePermission, check_course_permission
from ..models import Member

router = APIRouter(
    prefix="/api/v1/courses",
    tags=["courses"]
)

@router.post("/", response_model=schemas.Course, status_code=status.HTTP_201_CREATED)
def create_course(
    course: schemas.CourseCreate, 
    db: Session = Depends(database.get_db),
    current_member: Member = Depends(get_current_member)
):
    """
    创建新课程
    """
    if current_member.role not in [Permission.ADMIN, Permission.COACH]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    db_course = models.Course(**course.dict())
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course

@router.get("/", response_model=List[schemas.Course])
def list_courses(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(10, ge=1, le=100, description="每页记录数"),
    coach: Optional[str] = Query(None, description="按教练筛选"),
    location: Optional[str] = Query(None, description="按地点筛选"),
    db: Session = Depends(database.get_db)
):
    """
    获取课程列表（支持分页和筛选）
    """
    query = db.query(models.Course)
    
    if coach:
        query = query.filter(models.Course.coach == coach)
    if location:
        query = query.filter(models.Course.location == location)
    
    courses = query.offset(skip).limit(limit).all()
    return courses

@router.get("/{course_id}", response_model=schemas.Course)
def get_course(
    course_id: int, 
    db: Session = Depends(database.get_db),
    current_member: Member = Depends(check_course_permission(CoursePermission.VIEW, course_id))
):
    """
    获取单个课程详情
    """
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@router.put("/{course_id}", response_model=schemas.Course)
def update_course(
    course_id: int, 
    course_update: schemas.CourseUpdate, 
    db: Session = Depends(database.get_db),
    current_member: Member = Depends(get_current_member)
):
    if current_member.role not in [Permission.ADMIN, Permission.COACH]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    """
    更新课程信息
    """
    db_course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    update_data = course_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_course, field, value)
    
    db.commit()
    db.refresh(db_course)
    return db_course

@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: int, 
    db: Session = Depends(database.get_db),
    current_member: Member = Depends(get_current_member)
):
    if current_member.role != Permission.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    """
    删除课程
    """
    db_course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    db.delete(db_course)
    db.commit()
    return None


@router.post("/{course_id}/bookings", response_model=schemas.Booking, status_code=status.HTTP_201_CREATED)
def book_course(
    course_id: int,
    db: Session = Depends(database.get_db),
    current_member: Member = Depends(check_course_permission(CoursePermission.BOOK, course_id))
):
    """
    预约课程
    """
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # 检查课程容量
    current_bookings = db.query(models.Booking).filter(
        models.Booking.course_id == course_id,
        models.Booking.status == "confirmed"
    ).count()
    
    if current_bookings >= course.capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course is fully booked"
        )
    
    # 检查是否已经预约
    existing_booking = db.query(models.Booking).filter(
        models.Booking.member_id == current_member.id,
        models.Booking.course_id == course_id,
        models.Booking.status == "confirmed"
    ).first()
    
    if existing_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already booked this course"
        )
    
    booking = models.Booking(
        member_id=current_member.id,
        course_id=course_id,
        status="confirmed"
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking

@router.get("/{course_id}/bookings", response_model=List[schemas.Booking])
def get_course_bookings(
    course_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(database.get_db),
    current_member: Member = Depends(check_course_permission(CoursePermission.VIEW, course_id))
):
    """
    获取课程预约列表
    """
    bookings = db.query(models.Booking).filter(
        models.Booking.course_id == course_id
    ).offset(skip).limit(limit).all()
    return bookings