from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException

from .database import get_db, Coach, CoachSchedule
from .exceptions import ConflictException, NotFoundException
from .models import Course, CourseSchedule, CourseBooking


class ScheduleService:

    def get_course_schedule_by_id(self, schedule_id: int) -> CourseSchedule:
        """
        获取指定日期范围内的课程时间表

        Args:
            start_date: 开始日期
            end_date: 结束日期
            coach_id: 可选教练ID，用于筛选特定教练的课程

        Returns:
            List[CourseSchedule]: 课程时间表列表
        """
        query = self.db.query(CourseSchedule).filter(
            CourseSchedule.start_time >= start_date,
            CourseSchedule.end_time <= end_date
        )

        if coach_id:
            query = query.filter(CourseSchedule.coach_id == coach_id)

        return query.order_by(CourseSchedule.start_time).all()
        """
        根据ID获取课程时间表

        Args:
            schedule_id: 课程时间表ID

        Returns:
            CourseSchedule: 课程时间表

        Raises:
            NotFoundException: 如果课程时间表不存在
        """
        schedule = self.db.query(CourseSchedule).filter(
            CourseSchedule.id == schedule_id
        ).first()

        if not schedule:
            raise NotFoundException("课程时间表不存在")

        return schedule
        self,
        start_date: datetime,
        end_date: datetime,
        coach_id: Optional[int] = None
    ) -> List[CourseSchedule]:
        """
        获取指定日期范围内的课程时间表
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            coach_id: 可选教练ID，用于筛选特定教练的课程
            
        Returns:
            List[CourseSchedule]: 课程时间表列表
        """
        query = self.db.query(CourseSchedule).filter(
            CourseSchedule.start_time >= start_date,
            CourseSchedule.end_time <= end_date
        )
        
        if coach_id:
            query = query.filter(CourseSchedule.coach_id == coach_id)
            
        return query.order_by(CourseSchedule.start_time).all()
    """
    排班业务服务类，提供教练排班的冲突检测和空闲时间计算功能
    """

    def __init__(self, db: Session):
        self.db = db

    def check_schedule_conflict(
        self,
        coach_id: int,
        start_time: datetime,
        end_time: datetime,
        exclude_schedule_id: Optional[int] = None
    ) -> bool:
        """
        检查教练在指定时间段是否有排班冲突
        
        Args:
            coach_id: 教练ID
            start_time: 排班开始时间
            end_time: 排班结束时间
            exclude_schedule_id: 需要排除的排班ID（用于更新操作）
            
        Returns:
            bool: 是否存在冲突（True表示有冲突）
        """
        query = self.db.query(CoachSchedule).filter(
            CoachSchedule.coach_id == coach_id,
            CoachSchedule.start_time < end_time,
            CoachSchedule.end_time > start_time
        )
        
        if exclude_schedule_id:
            query = query.filter(CoachSchedule.id != exclude_schedule_id)
            
        conflicting_schedule = query.first()
        return conflicting_schedule is not None

    def get_coach_available_slots(
        self,
        coach_id: int,
        date: datetime,
        duration: timedelta = timedelta(hours=1)
    ) -> List[Tuple[datetime, datetime]]:
        """
        获取教练在指定日期的可用时间段
        
        Args:
            coach_id: 教练ID
            date: 查询日期
            duration: 期望的时段长度（默认为1小时）
            
        Returns:
            List[Tuple[datetime, datetime]]: 可用时间段列表，每个元素为(start_time, end_time)
        """
        # 获取教练当天的所有排班
        day_start = datetime.combine(date.date(), datetime.min.time())
        day_end = day_start + timedelta(days=1)
        
        schedules = self.db.query(CoachSchedule).filter(
            CoachSchedule.coach_id == coach_id,
            CoachSchedule.start_time >= day_start,
            CoachSchedule.end_time <= day_end
        ).order_by(CoachSchedule.start_time).all()
        
        # 默认工作时间为9:00-18:00
        default_start = datetime.combine(date.date(), datetime.strptime('09:00', '%H:%M').time())
        default_end = datetime.combine(date.date(), datetime.strptime('18:00', '%H:%M').time())
        
        # 如果没有排班，返回整个工作时间段
        if not schedules:
            return [(default_start, default_end)]
        
        available_slots = []
        
        # 检查第一个排班前的时间
        first_schedule = schedules[0]
        if first_schedule.start_time > default_start + duration:
            available_slots.append((default_start, first_schedule.start_time))
        
        # 检查排班之间的时间
        for i in range(len(schedules) - 1):
            current_end = schedules[i].end_time
            next_start = schedules[i+1].start_time
            
            if next_start - current_end >= duration:
                available_slots.append((current_end, next_start))
        
        # 检查最后一个排班后的时间
        last_schedule = schedules[-1]
        if default_end - last_schedule.end_time >= duration:
            available_slots.append((last_schedule.end_time, default_end))
            
        return available_slots

    def get_coach_schedules(
        self,
        coach_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> List[CoachSchedule]:
        """
        获取教练在指定日期范围内的所有排班
        
        Args:
            coach_id: 教练ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            List[CoachSchedule]: 排班列表
        """
        return self.db.query(CoachSchedule).filter(
            CoachSchedule.coach_id == coach_id,
            CoachSchedule.start_time >= start_date,
            CoachSchedule.end_time <= end_date
        ).order_by(CoachSchedule.start_time).all()

    def create_coach_schedule(
        self,
        coach_id: int,
        start_time: datetime,
        end_time: datetime,
        notes: Optional[str] = None
    ) -> CoachSchedule:
        """
        创建教练排班
        
        Args:
            coach_id: 教练ID
            start_time: 开始时间
            end_time: 结束时间
            notes: 备注信息
            
        Returns:
            CoachSchedule: 创建的排班记录
        """
        if self.check_schedule_conflict(coach_id, start_time, end_time):
            raise HTTPException(status_code=400, detail="教练在该时间段已有排班")
            
        if start_time >= end_time:
            raise HTTPException(status_code=400, detail="开始时间必须早于结束时间")
            
        schedule = CoachSchedule(
            coach_id=coach_id,
            start_time=start_time,
            end_time=end_time,
            notes=notes
        )
        
        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)
        
        return schedule

    def update_coach_schedule(
        self,
        schedule_id: int,
        start_time: datetime,
        end_time: datetime,
        notes: Optional[str] = None
    ) -> CoachSchedule:
        """
        更新教练排班
        
        Args:
            schedule_id: 排班ID
            start_time: 新的开始时间
            end_time: 新的结束时间
            notes: 新的备注信息
            
        Returns:
            CoachSchedule: 更新后的排班记录
        """
        schedule = self.db.query(CoachSchedule).filter(
            CoachSchedule.id == schedule_id
        ).first()
        
        if not schedule:
            raise HTTPException(status_code=404, detail="排班记录不存在")
            
        if self.check_schedule_conflict(
            schedule.coach_id,
            start_time,
            end_time,
            exclude_schedule_id=schedule_id
        ):
            raise ValueError("教练在该时间段已有排班")
            
        if start_time >= end_time:
            raise ValueError("开始时间必须早于结束时间")
            
        schedule.start_time = start_time
        schedule.end_time = end_time
        schedule.notes = notes
        
        self.db.commit()
        self.db.refresh(schedule)
        
        return schedule

    def check_course_booking_conflict(
    def book_course_slot(self, member_id: int, schedule_id: int) -> CourseBooking:
        """
        预约课程时间表

        Args:
            member_id: 会员ID
            schedule_id: 课程时间表ID

        Returns:
            CourseBooking: 创建的预约记录

        Raises:
            ConflictException: 如果时间冲突或没有可用位置
            NotFoundException: 如果课程时间表不存在
        """
        schedule = self.get_course_schedule_by_id(schedule_id)

        # 检查是否有可用位置
        if schedule.available_slots <= 0:
            raise ConflictException("该课程时间表已满")

        # 检查时间冲突
        if self.check_course_booking_conflict(member_id, schedule.start_time, schedule.end_time):
            raise ConflictException("会员在该时间段已有其他预约")

        # 创建预约记录
        booking = CourseBooking(
            member_id=member_id,
            schedule_id=schedule_id,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            booking_time=datetime.now(),
            status="confirmed"
        )

        # 更新可用位置
        schedule.available_slots -= 1

        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)

        return booking

    def cancel_course_booking(self, booking_id: int) -> None:
        """
        取消课程预约

        Args:
            booking_id: 预约ID

        Raises:
            NotFoundException: 如果预约记录不存在
        """
        booking = self.db.query(CourseBooking).filter(
            CourseBooking.id == booking_id
        ).first()

        if not booking:
            raise NotFoundException("预约记录不存在")

        # 获取关联的课程时间表
        schedule = self.get_course_schedule_by_id(booking.schedule_id)

        # 恢复可用位置
        schedule.available_slots += 1

        # 删除预约记录
        self.db.delete(booking)
        self.db.commit()
        self,
        member_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> bool:
        """
        检查会员在指定时间段是否有课程预约冲突
        
        Args:
            member_id: 会员ID
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            bool: 是否存在冲突（True表示有冲突）
        """
        conflicting_booking = self.db.query(CourseBooking).filter(
            CourseBooking.member_id == member_id,
            CourseBooking.start_time < end_time,
            CourseBooking.end_time > start_time
        ).first()
        
        return conflicting_booking is not None
        
    def get_member_bookings(self, member_id: int) -> List[CourseBooking]:
        """
        获取指定课程在日期范围内的可用时间段

        Args:
            course_id: 课程ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            List[CourseSchedule]: 可用课程时间表列表
        """
        return self.db.query(CourseSchedule).filter(
            CourseSchedule.course_id == course_id,
            CourseSchedule.start_time >= start_date,
            CourseSchedule.end_time <= end_date,
            CourseSchedule.available_slots > 0
        ).order_by(CourseSchedule.start_time).all()
        """
        获取会员的所有课程预约

        Args:
            member_id: 会员ID

        Returns:
            List[CourseBooking]: 预约记录列表
        """
        return self.db.query(CourseBooking).filter(
            CourseBooking.member_id == member_id
        ).order_by(CourseBooking.start_time.desc()).all()
        self,
        course_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> List[CourseSchedule]:
        """
        获取指定课程在日期范围内的可用时间段
        
        Args:
            course_id: 课程ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            List[CourseSchedule]: 可用课程时间表列表
        """
        return self.db.query(CourseSchedule).filter(
            CourseSchedule.course_id == course_id,
            CourseSchedule.start_time >= start_date,
            CourseSchedule.end_time <= end_date,
            CourseSchedule.available_slots > 0
        ).order_by(CourseSchedule.start_time).all()
        """
        删除教练排班

        Args:
            schedule_id: 排班ID

        Raises:
            HTTPException: 404 如果排班记录不存在
        """
        """
        删除教练排班
        
        Args:
            schedule_id: 排班ID
        """
        schedule = self.db.query(CoachSchedule).filter(
            CoachSchedule.id == schedule_id
        ).first()
        
        if schedule:
            self.db.delete(schedule)
            self.db.commit()

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
        """
        删除教练排班

        Args:
            schedule_id: 排班ID

        Raises:
            NotFoundException: 如果排班记录不存在
        """

# [AUTO-APPENDED] Failed to replace, adding new code:
        schedule = self.db.query(CoachSchedule).filter(
            CoachSchedule.id == schedule_id
        ).first()

        if not schedule:
            raise NotFoundException("排班记录不存在")
            
        self.db.delete(schedule)
        self.db.commit()