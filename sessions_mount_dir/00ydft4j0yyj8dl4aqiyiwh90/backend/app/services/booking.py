from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from fastapi_redis_cache import FastApiRedisCache, cache
import redis
from redis_lock import Lock
from sqlalchemy import select, update

from ..database import get_db
from ..config import settings
from ..models import Booking, Course


class BookingService:
    _redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True
    )
    def __init__(self, db: Session = next(get_db())):
        self.db = db

    @cache(expire=30)
    def create_booking(self, member_id: int, course_id: int) -> Booking:
        """
        创建新的课程预约
        :param member_id: 会员ID
        :param course_id: 课程ID
        :return: 创建的预约记录
        """
        # 获取分布式锁
        lock = Lock(self._redis_client, f"booking_lock:{member_id}:{course_id}")
        try:
            if not lock.acquire(blocking=True, timeout=5):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Another booking operation is in progress"
                )
            
            # 检查课程是否存在
            course = self.db.execute(
                select(Course).where(Course.id == course_id).with_for_update()
            ).scalar_one_or_none()
            
            if not course:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Course not found"
                )

            # 检查是否已经预约过该课程
            existing_booking = self.db.execute(
                select(Booking)
                .where(Booking.member_id == member_id)
                .where(Booking.course_id == course_id)
                .with_for_update()
            ).scalar_one_or_none()

            if existing_booking:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Already booked this course"
                )

            # 创建新的预约
            new_booking = Booking(
                member_id=member_id,
                course_id=course_id,
                booking_time=datetime.now(),
                status="confirmed"
            )

            self.db.add(new_booking)
            self.db.commit()
            self.db.refresh(new_booking)

            return new_booking
        finally:
            lock.release()

    @cache(expire=30)
    def cancel_booking(self, booking_id: int, member_id: int) -> Optional[Booking]:
        """
        取消课程预约
        :param booking_id: 预约ID
        :param member_id: 会员ID
        :return: 取消的预约记录
        """
        # 获取分布式锁
        lock = Lock(self._redis_client, f"cancel_lock:{booking_id}")
        try:
            if not lock.acquire(blocking=True, timeout=5):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Another cancellation operation is in progress"
                )
            
            # 使用乐观锁检查并更新
            result = self.db.execute(
                update(Booking)
                .where(Booking.id == booking_id)
                .where(Booking.member_id == member_id)
                .where(Booking.status == "confirmed")
                .values(status="cancelled")
                .returning(Booking)
            )
            
            booking = result.scalar_one_or_none()
            if not booking:
                # 检查是找不到预约还是状态不符合
                exists = self.db.execute(
                    select(Booking)
                    .where(Booking.id == booking_id)
                    .where(Booking.member_id == member_id)
                ).scalar_one_or_none()
                
                if not exists:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Booking not found"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot cancel booking with current status"
                    )
            
            self.db.commit()
            return booking
        finally:
            lock.release()

    @cache(expire=60)
    def get_member_bookings(self, member_id: int) -> list[Booking]:
        """
        获取会员的所有预约记录
        :param member_id: 会员ID
        :return: 预约记录列表
        """
        return self.db.query(Booking).filter(
            Booking.member_id == member_id
        ).all()

    @cache(expire=60)
    def get_course_bookings(self, course_id: int) -> list[Booking]:
        """
        获取课程的所有预约记录
        :param course_id: 课程ID
        :return: 预约记录列表
        """
        return self.db.query(Booking).filter(
            Booking.course_id == course_id
        ).all()