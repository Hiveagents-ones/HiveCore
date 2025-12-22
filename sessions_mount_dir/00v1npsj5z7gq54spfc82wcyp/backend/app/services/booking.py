from datetime import datetime, timedelta, date
from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import redis
import time
from contextlib import contextmanager
from fastapi import status
from ..middleware.audit import audit_log

from ..schemas.course import Course
from ..models.course_type import CourseType
from ..database import get_db
from ..services.rbac import has_permission, Role, Permission

# Redis连接配置
redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
# 预约限制配置
MAX_DAILY_BOOKINGS = 3
# 以下默认值将被课程类型配置覆盖
DEFAULT_CANCEL_TIME = timedelta(hours=1)
DEFAULT_BOOK_TIME = timedelta(minutes=30)
# 预约相关Redis键前缀
BOOKING_PREFIX = "booking:"
CANCEL_PREFIX = "cancel:"
BOOKING_LIMIT_PREFIX = "limit:"


class BookingService:
    """
    预约核心业务逻辑服务
    """

    @staticmethod
    @contextmanager
    def _get_redis_lock(lock_key: str, timeout: int = 30):
        """
        Redis分布式锁上下文管理器
        :param lock_key: 锁的键名
        :param timeout: 锁的超时时间(秒)
        """
        lock = False
        retry_count = 0
        while retry_count < retry:
            try:
                # 尝试获取锁
                lock = redis_client.set(lock_key, 'locked', nx=True, ex=timeout)
                if lock:
                    try:
                        yield
                        return
                    finally:
                        # 释放锁
                        redis_client.delete(lock_key)
                retry_count += 1
                if retry_count < retry:
                    time.sleep(delay)
            except redis.exceptions.RedisError as e:
                retry_count += 1
                if retry_count >= retry:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="系统繁忙，请稍后再试"
                    )
                time.sleep(delay)
        
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="操作过于频繁，请稍后再试"
        )
    @staticmethod
    @audit_log(action="course_booking")
    def book_course(db: Session, member_id: int, course_id: int) -> dict:
        """
        预约课程
        :param db: 数据库会话
        :param member_id: 会员ID
        :param course_id: 课程ID
        :return: 预约结果
        """
        # 使用Redis分布式锁防止并发问题
        lock_key = f"{BOOKING_PREFIX}{course_id}:{member_id}"
        with BookingService._get_redis_lock(lock_key):
            # 检查每日预约限制
            if not BookingService.check_booking_limit(db, member_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"每日最多预约{MAX_DAILY_BOOKINGS}次课程"
                )
        # 检查用户是否有预约权限
        if not has_permission(Permission.BOOK_COURSES, Role.MEMBER):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有预约课程的权限"
            )
        # 检查用户是否有取消预约权限
        if not has_permission(Permission.CANCEL_BOOKINGS, Role.MEMBER):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有取消预约的权限"
            )
        # 检查课程是否存在
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="课程不存在"
            )

        # 检查课程是否已过期
        # 检查课程是否已开始
        # 获取课程类型配置
        course_type = db.query(CourseType).filter(CourseType.id == course.type_id).first()
        if not course_type or not course_type.allow_booking:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该课程类型不允许预约"
            )
            
        min_book_time = timedelta(hours=course_type.min_booking_hours if course_type.min_booking_hours is not None else DEFAULT_BOOK_TIME.total_seconds()//3600)
        if datetime.now() > course.start_time - min_book_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"课程即将开始或已开始（需提前{min_book_time.seconds//3600}小时预约），无法预约"
            )
        if course.start_time < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="课程已过期"
            )

        # 检查是否已预约
        # 检查取消时间限制
        min_cancel_time = timedelta(hours=course_type.cancellation_hours if course_type.cancellation_hours is not None else DEFAULT_CANCEL_TIME.total_seconds()//3600)
        if datetime.now() > course.start_time - min_cancel_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"课程即将开始（需提前{min_cancel_time.seconds//3600}小时取消），无法取消预约"
            )
        # 检查预约人数限制
        if len(course.members) >= (course_type.max_capacity if course_type and course_type.max_capacity is not None else course.max_participants):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="课程人数已满"
            )
        if member_id in course.members:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="您已预约该课程"
            )

        # 执行预约
        try:
            course.members.append(member_id)
            # 更新每日预约计数
            today = date.today().isoformat()
            limit_key = f"{BOOKING_LIMIT_PREFIX}{member_id}:{today}"
            redis_client.incr(limit_key)
            redis_client.expire(limit_key, 86400)  # 24小时过期
            db.commit()
            db.refresh(course)
            return {
                "success": True,
                "message": "预约成功",
                "data": course
            }
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"预约失败: {str(e)}"
            )

    @staticmethod
    @audit_log(action="course_cancel")
    def cancel_booking(db: Session, member_id: int, course_id: int) -> dict:
        """
        取消预约
        :param db: 数据库会话
        :param member_id: 会员ID
        :param course_id: 课程ID
        :return: 取消结果
        """
        # 使用Redis分布式锁防止并发问题
        lock_key = f"{CANCEL_PREFIX}{course_id}:{member_id}"
        with BookingService._get_redis_lock(lock_key):
        # 检查课程是否存在
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="课程不存在"
            )

        # 检查是否已预约
        if member_id not in course.members:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="您未预约该课程"
            )

        # 执行取消预约
        try:
            course.members.remove(member_id)
            db.commit()
            db.refresh(course)
            return {
                "success": True,
                "message": "取消预约成功",
                "data": course
            }
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"取消预约失败: {str(e)}"
            )

    @staticmethod
    def get_member_bookings(db: Session, member_id: int) -> list:

    @staticmethod
    def check_booking_limit(db: Session, member_id: int) -> bool:
        """
        检查会员预约限制
        :param db: 数据库会话
        :param member_id: 会员ID
        :return: 是否超过限制
        """
        """
        检查会员预约限制
        :param db: 数据库会话
        :param member_id: 会员ID
        :return: 是否超过限制
        """
        # 使用Redis记录每日预约次数
        today = datetime.now().strftime("%Y-%m-%d")
        limit_key = f"{BOOKING_LIMIT_PREFIX}{member_id}:{today}"
        
        # 获取当前预约次数
        count = redis_client.get(limit_key)
        if count and int(count) >= 3:  # 每日最多预约3次
            return False
        return True
        """
        获取会员所有预约课程
        :param db: 数据库会话
        :param member_id: 会员ID
        :return: 预约课程列表
        """
        courses = db.query(Course).filter(Course.members.any(member_id)).all()
        return courses

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    @staticmethod
    @contextmanager
    def _get_redis_lock(lock_key: str, timeout: int = 30, retry: int = 3, delay: float = 0.1):
        """
        Redis分布式锁上下文管理器
        :param lock_key: 锁的键名
        :param timeout: 锁的超时时间(秒)
        :param retry: 重试次数
        :param delay: 重试间隔(秒)
        """
        lock = False
        retry_count = 0
        while retry_count < retry:
            try:
                # 尝试获取锁
                lock = redis_client.set(lock_key, 'locked', nx=True, ex=timeout)
                if lock:
                    try:
                        yield
                        return
                    finally:
                        # 释放锁
                        redis_client.delete(lock_key)
                retry_count += 1
                if retry_count < retry:
                    time.sleep(delay)
            except redis.exceptions.RedisError as e:
                retry_count += 1
                if retry_count >= retry:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="系统繁忙，请稍后再试"
                    )
                time.sleep(delay)

        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="操作过于频繁，请稍后再试"
        )