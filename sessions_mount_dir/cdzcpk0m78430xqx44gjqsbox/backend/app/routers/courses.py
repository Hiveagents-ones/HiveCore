from datetime import datetime
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from jose import jwt
import os
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..schemas import courses as schemas
from ..models import courses as models
from ..database import get_db

router = APIRouter(
    dependencies=[Depends(HTTPBearer())],
    prefix="/api/v1/courses",
    tags=["courses"]
)


@router.get("/", response_model=List[schemas.Course])
def get_courses(request: Request, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取所有课程列表"""
    token = request.headers.get("Authorization")
    if not token:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=jsonable_encoder({"detail": "Not authenticated"})
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.JWTError:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=jsonable_encoder({"detail": "Invalid token"})
        )
    """获取所有课程列表"""
    db_courses = db.query(models.Course).offset(skip).limit(limit).all()
    return db_courses


@router.post("/", response_model=schemas.Course, status_code=status.HTTP_201_CREATED)
def create_course(request: Request, course: schemas.CourseCreate, db: Session = Depends(get_db)):
    """创建新课程"""
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    """创建新课程"""
    db_course = models.Course(**course.dict())
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course


@router.get("/{course_id}", response_model=schemas.CourseWithBookings)
def get_course(request: Request, course_id: int, db: Session = Depends(get_db)):
    """获取课程详情及预约信息"""
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    """获取课程详情及预约信息"""
    db_course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    return db_course


@router.put("/{course_id}", response_model=schemas.Course)
def update_course(request: Request, course_id: int, course: schemas.CourseUpdate, db: Session = Depends(get_db)):
    """更新课程信息"""
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    """更新课程信息"""
    db_course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    update_data = course.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_course, field, value)
    
    db.commit()
    db.refresh(db_course)
    return db_course


@router.get("/{course_id}/bookings", response_model=List[schemas.Booking])
def get_course_bookings(request: Request, course_id: int, db: Session = Depends(get_db)):
    """获取课程的所有预约记录"""
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    """获取课程的所有预约记录"""
    db_bookings = db.query(models.Booking).filter(models.Booking.course_id == course_id).all()
    return db_bookings


@router.post("/{course_id}/bookings", response_model=schemas.Booking, status_code=status.HTTP_201_CREATED)
def create_booking(request: Request, course_id: int, booking: schemas.BookingCreate, db: Session = Depends(get_db)):
    """创建课程预约"""
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    # 检查课程容量
    db_course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    if db_course.current_bookings >= db_course.max_capacity:
        raise HTTPException(status_code=400, detail="Course is full")
    """创建课程预约"""
    # 检查课程是否存在
    db_course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # 检查是否已经预约过
    existing_booking = db.query(models.Booking).filter(
        models.Booking.member_id == booking.member_id,
        models.Booking.course_id == course_id
    ).first()
    
    if existing_booking:
        raise HTTPException(status_code=400, detail="Already booked this course")
    
    db_booking = models.Booking(
        member_id=booking.member_id,
        course_id=course_id,
        status=booking.status,
        booking_time=datetime.now()
    )
    
    # 更新课程预约计数
    db_course.current_bookings += 1
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


@router.delete("/{course_id}/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_booking(request: Request, course_id: int, booking_id: int, db: Session = Depends(get_db)):
    """取消课程预约"""
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    """取消课程预约"""
    db_booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.course_id == course_id
    ).first()
    
    if not db_booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    db.delete(db_booking)
    # 更新课程预约计数
    db_course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if db_course and db_course.current_bookings > 0:
        db_course.current_bookings -= 1
    db.commit()
    return None