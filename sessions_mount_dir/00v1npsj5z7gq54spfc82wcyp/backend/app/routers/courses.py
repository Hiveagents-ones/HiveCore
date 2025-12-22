from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..schemas.course import Course, CourseCreate, CourseUpdate, CourseBooking, CourseScheduleQuery
from ..database import get_db
from ..services.booking import BookingService
from ..middleware.audit import audit_log
from ..services.rbac import has_permission, Role, Permission

router = APIRouter(
    prefix="/api/v1/courses",
    tags=["courses"]
)


@has_permission(roles=[Role.ADMIN, Role.COACH, Role.MEMBER], permissions=[Permission.READ])
@router.get("/", response_model=List[Course])
@audit_log(action="get_courses")
def get_courses(
    query: CourseScheduleQuery = Depends(),
    db: Session = Depends(get_db)
):
    """
    获取课程列表
    
    参数:
    - start_date: 开始日期
    - end_date: 结束日期
    - coach_id: 教练ID
    
    返回:
    - 符合条件的课程列表
    """
    # 这里应该实现数据库查询逻辑
    # 示例代码，实际需要替换为真实数据库查询
    from ..models import Course as DBCourse
    
    query_params = {}
    if query.start_date:
        query_params["start_time"] = query.start_date
    if query.end_date:
        query_params["end_time"] = query.end_date
    if query.coach_id:
        query_params["coach_id"] = query.coach_id
    
    courses = db.query(DBCourse).filter_by(**query_params).all()
    return courses


@has_permission(roles=[Role.ADMIN, Role.MEMBER], permissions=[Permission.CREATE])
@router.post("/book", response_model=CourseBooking)
@audit_log(action="book_course")
def book_course(
    booking: CourseBooking,
    db: Session = Depends(get_db),
    booking_service: BookingService = Depends(BookingService)
):
    """
    预约课程
    
    参数:
    - member_id: 会员ID
    - course_id: 课程ID
    
    返回:
    - 预约信息
    """
    # 这里应该实现预约逻辑
    # 示例代码，实际需要替换为真实数据库操作
    from ..models import CourseBooking as DBCourseBooking
    
    # 检查课程是否存在
    from ..models import Course as DBCourse
    course = db.query(DBCourse).filter(DBCourse.id == booking.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # 检查会员是否存在
    from ..models import Member as DBMember
    member = db.query(DBMember).filter(DBMember.id == booking.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # 检查是否已经预约
    existing_booking = db.query(DBCourseBooking).filter(
        DBCourseBooking.member_id == booking.member_id,
        DBCourseBooking.course_id == booking.course_id
    ).first()
    
    if existing_booking:
        raise HTTPException(status_code=400, detail="Already booked this course")
    
    # 创建预约
    db_booking = DBCourseBooking(**booking.dict())
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    
    return db_booking


@has_permission(roles=[Role.ADMIN, Role.MEMBER], permissions=[Permission.DELETE])
@router.delete("/book")
@audit_log(action="cancel_booking")
def cancel_booking(
    booking: CourseBooking,
    db: Session = Depends(get_db),
    booking_service: BookingService = Depends(BookingService)
):
    """
    取消课程预约
    
    参数:
    - member_id: 会员ID
    - course_id: 课程ID
    
    返回:
    - 操作结果
    """
    # 这里应该实现取消预约逻辑
    # 示例代码，实际需要替换为真实数据库操作
    from ..models import CourseBooking as DBCourseBooking
    
    # 查找并删除预约记录
    booking_record = db.query(DBCourseBooking).filter(
        DBCourseBooking.member_id == booking.member_id,
        DBCourseBooking.course_id == booking.course_id
    ).first()
    
    if not booking_record:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    db.delete(booking_record)
    db.commit()
    
    return {"message": "Booking cancelled successfully"}