from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from ..models.course import Course, Booking
from ..schemas.course import CourseCreate, CourseUpdate, BookingCreate, BookingUpdate

class CourseCRUD:
    def get(self, db: Session, course_id: int) -> Optional[Course]:
        """获取单个课程"""
        return db.query(Course).filter(Course.id == course_id).first()

    def get_multi(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        instructor: Optional[str] = None,
        location: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Course]:
        """获取课程列表"""
        query = db.query(Course)
        
        if instructor:
            query = query.filter(Course.instructor.ilike(f"%{instructor}%"))
        if location:
            query = query.filter(Course.location.ilike(f"%{location}%"))
        if is_active is not None:
            query = query.filter(Course.is_active == is_active)
            
        return query.offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: CourseCreate) -> Course:
        """创建新课程"""
        db_obj = Course(
            title=obj_in.title,
            description=obj_in.description,
            instructor=obj_in.instructor,
            capacity=obj_in.capacity,
            start_time=obj_in.start_time,
            end_time=obj_in.end_time,
            location=obj_in.location,
            is_active=obj_in.is_active
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, 
        db: Session, 
        db_obj: Course, 
        obj_in: CourseUpdate
    ) -> Course:
        """更新课程"""
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, course_id: int) -> Optional[Course]:
        """删除课程"""
        obj = db.query(Course).get(course_id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

    def get_available_slots(self, db: Session, course_id: int) -> int:
        """获取课程剩余名额"""
        course = self.get(db, course_id)
        if not course:
            return 0
        
        booked_count = db.query(Booking).filter(
            and_(
                Booking.course_id == course_id,
                Booking.is_cancelled == False
            )
        ).count()
        
        return max(0, course.capacity - booked_count)

class BookingCRUD:
    def get(self, db: Session, booking_id: int) -> Optional[Booking]:
        """获取单个预约"""
        return db.query(Booking).filter(Booking.id == booking_id).first()

    def get_multi(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        user_id: Optional[int] = None,
        course_id: Optional[int] = None,
        is_cancelled: Optional[bool] = None
    ) -> List[Booking]:
        """获取预约列表"""
        query = db.query(Booking)
        
        if user_id:
            query = query.filter(Booking.user_id == user_id)
        if course_id:
            query = query.filter(Booking.course_id == course_id)
        if is_cancelled is not None:
            query = query.filter(Booking.is_cancelled == is_cancelled)
            
        return query.offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: BookingCreate) -> Booking:
        """创建新预约"""
        # 检查是否已经预约
        existing = db.query(Booking).filter(
            and_(
                Booking.user_id == obj_in.user_id,
                Booking.course_id == obj_in.course_id,
                Booking.is_cancelled == False
            )
        ).first()
        
        if existing:
            raise ValueError("User has already booked this course")
        
        # 检查课程是否还有名额
        course_crud = CourseCRUD()
        available = course_crud.get_available_slots(db, obj_in.course_id)
        if available <= 0:
            raise ValueError("No available slots for this course")
        
        db_obj = Booking(
            user_id=obj_in.user_id,
            course_id=obj_in.course_id
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def cancel(self, db: Session, booking_id: int) -> Optional[Booking]:
        """取消预约"""
        booking = self.get(db, booking_id)
        if booking and not booking.is_cancelled:
            booking.is_cancelled = True
            booking.cancelled_at = func.now()
            db.add(booking)
            db.commit()
            db.refresh(booking)
        return booking

    def get_user_bookings(
        self, 
        db: Session, 
        user_id: int,
        include_cancelled: bool = False
    ) -> List[Booking]:
        """获取用户的所有预约"""
        query = db.query(Booking).filter(Booking.user_id == user_id)
        if not include_cancelled:
            query = query.filter(Booking.is_cancelled == False)
        return query.all()

    def get_course_bookings(
        self, 
        db: Session, 
        course_id: int,
        include_cancelled: bool = False
    ) -> List[Booking]:
        """获取课程的所有预约"""
        query = db.query(Booking).filter(Booking.course_id == course_id)
        if not include_cancelled:
            query = query.filter(Booking.is_cancelled == False)
        return query.all()

# 创建CRUD实例
course = CourseCRUD()
booking = BookingCRUD()
