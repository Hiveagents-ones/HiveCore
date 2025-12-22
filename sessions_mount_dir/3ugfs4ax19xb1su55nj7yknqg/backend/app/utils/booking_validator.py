from datetime import datetime, timedelta
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import Course, CourseSchedule, Member


class BookingValidator:
    """
    预约规则校验工具类，包含各种预约相关的校验规则
    """

    @staticmethod
    def validate_booking_time(
        db: Session, 
        schedule_id: int, 
        booking_time: datetime
    ) -> Tuple[bool, str]:
        """
        校验预约时间是否合法
        
        Args:
            db: 数据库会话
            schedule_id: 课程安排ID
            booking_time: 预约时间
            
        Returns:
            Tuple[是否合法, 错误信息]
        """
        # 获取课程安排
        schedule = db.query(CourseSchedule).filter(
            CourseSchedule.id == schedule_id
        ).first()
        
        if not schedule:
            return False, "课程安排不存在"
            
        # 检查预约时间是否在课程开始前24小时到课程开始前1小时之间
        min_booking_time = schedule.start_time - timedelta(hours=24)
        max_booking_time = schedule.start_time - timedelta(hours=1)
        
        if booking_time < min_booking_time:
            return False, "预约时间过早，最早可提前24小时预约"
            
        if booking_time > max_booking_time:
            return False, "预约时间过晚，最晚可提前1小时预约"
            
        return True, ""

    @staticmethod
    def validate_member_eligibility(
        db: Session, 
        member_id: int, 
        course_id: int
    ) -> Tuple[bool, str]:
        """
        校验会员是否有资格预约该课程
        
        Args:
            db: 数据库会话
            member_id: 会员ID
            course_id: 课程ID
            
        Returns:
            Tuple[是否合法, 错误信息]
        """
        # 检查会员是否存在
        member = db.query(Member).filter(Member.id == member_id).first()
        if not member:
            return False, "会员不存在"
            
        # 检查课程是否存在
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return False, "课程不存在"
            
        # 检查会员类型是否符合课程要求
        if course.membership_required and member.membership_type != course.membership_required:
            return False, f"该课程需要{course.membership_required}会员资格"
            
        return True, ""

    @staticmethod
    def validate_course_availability(
        db: Session, 
        schedule_id: int
    ) -> Tuple[bool, str]:
        """
        校验课程是否还有空位
        
        Args:
            db: 数据库会话
            schedule_id: 课程安排ID
            
        Returns:
            Tuple[是否合法, 错误信息]
        """
        schedule = db.query(CourseSchedule).filter(
            CourseSchedule.id == schedule_id
        ).first()
        
        if not schedule:
            return False, "课程安排不存在"
            
        course = db.query(Course).filter(Course.id == schedule.course_id).first()
        if not course:
            return False, "课程不存在"
            
        # 获取当前已预约人数
        current_bookings = len(schedule.bookings)
        
        if current_bookings >= course.capacity:
            return False, "课程已满"
            
        return True, ""

    @staticmethod
    def validate_booking_conflicts(
        db: Session, 
        member_id: int, 
        schedule_id: int
    ) -> Tuple[bool, str]:
        """
        校验会员是否有时间冲突的预约
        
        Args:
            db: 数据库会话
            member_id: 会员ID
            schedule_id: 课程安排ID
            
        Returns:
            Tuple[是否合法, 错误信息]
        """
        # 获取目标课程安排
        target_schedule = db.query(CourseSchedule).filter(
            CourseSchedule.id == schedule_id
        ).first()
        
        if not target_schedule:
            return False, "课程安排不存在"
            
        # 获取会员所有已预约的课程安排
        member_schedules = db.query(CourseSchedule).join(
            CourseSchedule.bookings
        ).filter(
            CourseSchedule.bookings.any(member_id=member_id)
        ).all()
        
        # 检查时间冲突
        for schedule in member_schedules:
            if (
                schedule.start_time < target_schedule.end_time and
                schedule.end_time > target_schedule.start_time
            ):
                return False, "与已有预约时间冲突"
                
        return True, ""