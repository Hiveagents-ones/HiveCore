from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import List
from ...models import Booking, Course
from ...database import db

router = APIRouter()

class BookingCreate(BaseModel):
    course_id: int
    start_time: datetime
    end_time: datetime

@router.post("/", response_model=Booking)
async def create_booking(booking: BookingCreate):
    # 检查课程是否存在
    course = await db.query(Course).get(booking.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # 检查人数限制
    current_bookings = await db.query(Booking).filter(Booking.course_id == course.id).count()
    if current_bookings >= course.max_capacity:
        raise HTTPException(status_code=400, detail="Course is full")

    # 检查时间冲突
    existing_bookings = await db.query(Booking).filter(
        Booking.course_id == course.id,
        Booking.start_time < booking.end_time,
        Booking.end_time > booking.start_time
    ).all()

    if existing_bookings:
        raise HTTPException(status_code=400, detail="Time conflict with existing booking")

    # 创建新预约
    new_booking = Booking(
        course_id=booking.course_id,
        start_time=booking.start_time,
        end_time=booking.end_time
    )
    db.add(new_booking)
    await db.commit()
    await db.refresh(new_booking)
    return new_booking