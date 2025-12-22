from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .... import crud, schemas
from ....database import get_db

router = APIRouter()

@router.post("/", response_model=schemas.Course, status_code=status.HTTP_201_CREATED)
def create_course(course: schemas.CourseCreate, db: Session = Depends(get_db)):
    """创建新课程"""
    return crud.create_course(db=db, course=course)

@router.get("/", response_model=List[schemas.Course])
def read_courses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取课程列表（支持分页）"""
    courses = crud.get_courses(db, skip=skip, limit=limit)
    return courses

@router.get("/{course_id}", response_model=schemas.Course)
def read_course(course_id: int, db: Session = Depends(get_db)):
    """获取单个课程信息"""
    db_course = crud.get_course(db, course_id=course_id)
    if db_course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return db_course

@router.put("/{course_id}", response_model=schemas.Course)
def update_course(course_id: int, course: schemas.CourseUpdate, db: Session = Depends(get_db)):
    """更新课程信息"""
    db_course = crud.update_course(db, course_id=course_id, course=course)
    if db_course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return db_course

@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: int, db: Session = Depends(get_db)):
    """删除课程"""
    success = crud.delete_course(db, course_id=course_id)
    if not success:
        raise HTTPException(status_code=404, detail="Course not found")
    return None

@router.post("/{course_id}/book", response_model=schemas.Booking, status_code=status.HTTP_201_CREATED)
def book_course(course_id: int, booking: schemas.BookingCreate, db: Session = Depends(get_db)):
    """预约课程"""
    # 确保预约的课程ID与URL中的课程ID一致
    booking.course_id = course_id
    
    # 检查课程是否存在
    db_course = crud.get_course(db, course_id=course_id)
    if db_course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # 检查会员是否存在
    db_member = crud.get_member(db, member_id=booking.member_id)
    if db_member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # 检查课程是否已满
    if not crud.is_course_available(db, course_id=course_id):
        raise HTTPException(status_code=400, detail="Course is fully booked")
    
    # 检查会员是否已经预约了该课程
    existing_booking = crud.get_booking_by_member_and_course(db, member_id=booking.member_id, course_id=course_id)
    if existing_booking:
        raise HTTPException(status_code=400, detail="Member has already booked this course")
    
    return crud.create_booking(db=db, booking=booking)

@router.delete("/{course_id}/book/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_booking(course_id: int, booking_id: int, db: Session = Depends(get_db)):
    """取消预约"""
    # 检查预约是否存在
    db_booking = crud.get_booking(db, booking_id=booking_id)
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # 确保预约的课程ID与URL中的课程ID一致
    if db_booking.course_id != course_id:
        raise HTTPException(status_code=400, detail="Booking does not belong to this course")
    
    success = crud.delete_booking(db, booking_id=booking_id)
    if not success:
        raise HTTPException(status_code=404, detail="Booking not found")
    return None

@router.get("/{course_id}/bookings", response_model=List[schemas.Booking])
def read_course_bookings(course_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取课程的所有预约"""
    # 检查课程是否存在
    db_course = crud.get_course(db, course_id=course_id)
    if db_course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return crud.get_bookings_by_course(db, course_id=course_id, skip=skip, limit=limit)
