from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import Query
from fastapi import Header
from fastapi import Path
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Course, CourseSchedule, CourseBooking, Member
from ..schemas import CourseCreate, CourseScheduleCreate, CourseBookingCreate, CourseResponse, CourseScheduleResponse, CourseBookingResponse

router = APIRouter(
    prefix="/api/v1/courses",
    tags=["courses"]
)

@router.get("/", response_model=List[CourseResponse])
def get_courses(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    language: str = Query(None, description="Filter courses by language"),
    name: str = Query(None, description="Filter courses by name"),
    accept_language: str = Header(None, description="Preferred client language")
):
    """获取所有课程列表"""
    query = db.query(Course)
    
    if not language and accept_language:
        # Use client preferred language if no explicit filter provided
        language = accept_language.split(',')[0].split(';')[0].strip()
        
    if language:
        query = query.filter(Course.language == language)
    if name:
        query = query.filter(Course.name.ilike(f'%{name}%'))
        
    courses = query.offset(skip).limit(limit).all()
    return courses

@router.post("/", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
@router.put("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: int = Path(..., description="The ID of the course to update"),
    course: CourseCreate,
    db: Session = Depends(get_db)
):
    """更新课程信息"""
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    for key, value in course.dict().items():
        setattr(db_course, key, value)
    
    db.commit()
    db.refresh(db_course)
    return db_course

@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: int = Path(..., description="The ID of the course to delete"),
    db: Session = Depends(get_db)
):
    """删除课程"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    db.delete(course)
    db.commit()
    return {"message": "Course deleted successfully"}
def create_course(course: CourseCreate, db: Session = Depends(get_db)):
    """创建新课程"""
    db_course = Course(**course.dict())
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course

@router.get("/schedule", response_model=List[CourseScheduleResponse])
def get_course_schedules(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    language: str = Query(None, description="Filter schedules by course language"),
    accept_language: str = Header(None, description="Preferred client language")
):
    """获取课程安排列表"""
    query = db.query(CourseSchedule)
    
    if not language and accept_language:
        # Use client preferred language if no explicit filter provided
        language = accept_language.split(',')[0].split(';')[0].strip()
        
    if language:
        query = query.join(Course).filter(Course.language == language)
        
    schedules = query.offset(skip).limit(limit).all()
    return schedules

@router.post("/schedule", response_model=CourseScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_course_schedule(schedule: CourseScheduleCreate, db: Session = Depends(get_db)):
    """创建课程安排"""
    db_schedule = CourseSchedule(**schedule.dict())
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule

@router.get("/{course_id}/bookings", response_model=List[CourseBookingResponse])
def get_course_bookings(course_id: int, db: Session = Depends(get_db)):
    """获取特定课程的预约列表"""
    bookings = db.query(CourseBooking).filter(CourseBooking.schedule_id == course_id).all()
    return bookings

@router.post("/{course_id}/bookings", response_model=CourseBookingResponse, status_code=status.HTTP_201_CREATED)
def create_course_booking(course_id: int, booking: CourseBookingCreate, db: Session = Depends(get_db)):
    """预约课程"""
    # 检查会员是否存在
    member = db.query(Member).filter(Member.id == booking.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # 检查课程安排是否存在
    schedule = db.query(CourseSchedule).filter(CourseSchedule.id == course_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Course schedule not found")
    
    # 检查是否已预约
    existing_booking = db.query(CourseBooking).filter(
        CourseBooking.member_id == booking.member_id,
        CourseBooking.schedule_id == course_id
    ).first()
    
    if existing_booking:
        raise HTTPException(status_code=400, detail="Already booked this course")
    
    db_booking = CourseBooking(**booking.dict(), schedule_id=course_id)
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking

@router.delete("/{course_id}/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_course_booking(course_id: int, booking_id: int, db: Session = Depends(get_db)):
    """取消课程预约"""
    booking = db.query(CourseBooking).filter(
        CourseBooking.id == booking_id,
        CourseBooking.schedule_id == course_id
    ).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    db.delete(booking)
    db.commit()
    return {"message": "Booking cancelled successfully"}