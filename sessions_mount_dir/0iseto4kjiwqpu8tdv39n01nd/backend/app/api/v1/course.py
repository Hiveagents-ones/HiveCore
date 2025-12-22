from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ....core.deps import get_db, get_current_user
from ....models.user import User
from ....models.course import Course as CourseModel, Booking as BookingModel
from ....schemas.course import (
    Course as CourseSchema,
    CourseCreate,
    CourseUpdate,
    CourseList,
    Booking as BookingSchema,
    BookingCreate,
    BookingUpdate,
    BookingList,
)

router = APIRouter()


@router.get("/", response_model=CourseList)
def list_courses(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=100, description="返回的记录数"),
    instructor: Optional[str] = Query(None, description="教练姓名筛选"),
    location: Optional[str] = Query(None, description="地点筛选"),
    start_date: Optional[datetime] = Query(None, description="开始日期筛选"),
    end_date: Optional[datetime] = Query(None, description="结束日期筛选"),
    is_active: Optional[bool] = Query(True, description="是否激活"),
    db: Session = Depends(get_db),
):
    """
    获取课程列表
    """
    query = db.query(CourseModel)
    
    if instructor:
        query = query.filter(CourseModel.instructor.ilike(f"%{instructor}%"))
    if location:
        query = query.filter(CourseModel.location.ilike(f"%{location}%"))
    if start_date:
        query = query.filter(CourseModel.start_time >= start_date)
    if end_date:
        query = query.filter(CourseModel.end_time <= end_date)
    if is_active is not None:
        query = query.filter(CourseModel.is_active == is_active)
    
    total = query.count()
    courses = query.offset(skip).limit(limit).all()
    
    # 计算每个课程的预约信息
    course_list = []
    for course in courses:
        current_bookings = db.query(BookingModel).filter(
            and_(
                BookingModel.course_id == course.id,
                BookingModel.is_cancelled == False
            )
        ).count()
        
        course_data = CourseSchema(
            id=course.id,
            name=course.name,
            description=course.description,
            instructor=course.instructor,
            capacity=course.capacity,
            start_time=course.start_time,
            end_time=course.end_time,
            location=course.location,
            is_active=course.is_active,
            created_at=course.created_at,
            updated_at=course.updated_at,
            current_bookings=current_bookings,
            available_spots=course.capacity - current_bookings
        )
        course_list.append(course_data)
    
    return CourseList(courses=course_list, total=total)


@router.get("/{course_id}", response_model=CourseSchema)
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
):
    """
    获取单个课程详情
    """
    course = db.query(CourseModel).filter(CourseModel.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在"
        )
    
    current_bookings = db.query(BookingModel).filter(
        and_(
            BookingModel.course_id == course.id,
            BookingModel.is_cancelled == False
        )
    ).count()
    
    return CourseSchema(
        id=course.id,
        name=course.name,
        description=course.description,
        instructor=course.instructor,
        capacity=course.capacity,
        start_time=course.start_time,
        end_time=course.end_time,
        location=course.location,
        is_active=course.is_active,
        created_at=course.created_at,
        updated_at=course.updated_at,
        current_bookings=current_bookings,
        available_spots=course.capacity - current_bookings
    )


@router.post("/", response_model=CourseSchema, status_code=status.HTTP_201_CREATED)
def create_course(
    course: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建新课程（需要管理员权限）
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    
    if course.start_time >= course.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="开始时间必须早于结束时间"
        )
    
    db_course = CourseModel(**course.dict())
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    
    return CourseSchema(
        id=db_course.id,
        name=db_course.name,
        description=db_course.description,
        instructor=db_course.instructor,
        capacity=db_course.capacity,
        start_time=db_course.start_time,
        end_time=db_course.end_time,
        location=db_course.location,
        is_active=db_course.is_active,
        created_at=db_course.created_at,
        updated_at=db_course.updated_at,
        current_bookings=0,
        available_spots=db_course.capacity
    )


@router.put("/{course_id}", response_model=CourseSchema)
def update_course(
    course_id: int,
    course_update: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新课程信息（需要管理员权限）
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    
    db_course = db.query(CourseModel).filter(CourseModel.id == course_id).first()
    if not db_course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在"
        )
    
    update_data = course_update.dict(exclude_unset=True)
    
    # 检查时间合理性
    if "start_time" in update_data and "end_time" in update_data:
        if update_data["start_time"] >= update_data["end_time"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="开始时间必须早于结束时间"
            )
    elif "start_time" in update_data:
        if update_data["start_time"] >= db_course.end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="开始时间必须早于结束时间"
            )
    elif "end_time" in update_data:
        if db_course.start_time >= update_data["end_time"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="开始时间必须早于结束时间"
            )
    
    # 检查容量是否小于当前预约数
    if "capacity" in update_data:
        current_bookings = db.query(BookingModel).filter(
            and_(
                BookingModel.course_id == course_id,
                BookingModel.is_cancelled == False
            )
        ).count()
        if update_data["capacity"] < current_bookings:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"新容量不能小于当前预约数 {current_bookings}"
            )
    
    for field, value in update_data.items():
        setattr(db_course, field, value)
    
    db_course.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_course)
    
    current_bookings = db.query(BookingModel).filter(
        and_(
            BookingModel.course_id == db_course.id,
            BookingModel.is_cancelled == False
        )
    ).count()
    
    return CourseSchema(
        id=db_course.id,
        name=db_course.name,
        description=db_course.description,
        instructor=db_course.instructor,
        capacity=db_course.capacity,
        start_time=db_course.start_time,
        end_time=db_course.end_time,
        location=db_course.location,
        is_active=db_course.is_active,
        created_at=db_course.created_at,
        updated_at=db_course.updated_at,
        current_bookings=current_bookings,
        available_spots=db_course.capacity - current_bookings
    )


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除课程（需要管理员权限）
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    
    db_course = db.query(CourseModel).filter(CourseModel.id == course_id).first()
    if not db_course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在"
        )
    
    # 检查是否有未取消的预约
    active_bookings = db.query(BookingModel).filter(
        and_(
            BookingModel.course_id == course_id,
            BookingModel.is_cancelled == False
        )
    ).count()
    
    if active_bookings > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="课程有未取消的预约，无法删除"
        )
    
    db.delete(db_course)
    db.commit()


@router.post("/{course_id}/book", response_model=BookingSchema, status_code=status.HTTP_201_CREATED)
def book_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    预约课程
    """
    # 检查课程是否存在并激活
    course = db.query(CourseModel).filter(
        and_(
            CourseModel.id == course_id,
            CourseModel.is_active == True
        )
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在或已关闭"
        )
    
    # 检查课程时间是否已过
    if course.start_time <= datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="课程已开始，无法预约"
        )
    
    # 检查用户是否已预约过该课程
    existing_booking = db.query(BookingModel).filter(
        and_(
            BookingModel.course_id == course_id,
            BookingModel.user_id == current_user.id,
            BookingModel.is_cancelled == False
        )
    ).first()
    
    if existing_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已经预约了该课程"
        )
    
    # 检查课程容量
    current_bookings = db.query(BookingModel).filter(
        and_(
            BookingModel.course_id == course_id,
            BookingModel.is_cancelled == False
        )
    ).count()
    
    if current_bookings >= course.capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="课程已满员"
        )
    
    # 创建预约
    booking = BookingModel(
        user_id=current_user.id,
        course_id=course_id,
        booked_at=datetime.utcnow(),
        is_cancelled=False
    )
    
    db.add(booking)
    db.commit()
    db.refresh(booking)
    
    # 返回预约信息
    current_bookings = db.query(BookingModel).filter(
        and_(
            BookingModel.course_id == course.id,
            BookingModel.is_cancelled == False
        )
    ).count()
    
    course_schema = CourseSchema(
        id=course.id,
        name=course.name,
        description=course.description,
        instructor=course.instructor,
        capacity=course.capacity,
        start_time=course.start_time,
        end_time=course.end_time,
        location=course.location,
        is_active=course.is_active,
        created_at=course.created_at,
        updated_at=course.updated_at,
        current_bookings=current_bookings,
        available_spots=course.capacity - current_bookings
    )
    
    return BookingSchema(
        id=booking.id,
        user_id=booking.user_id,
        course_id=booking.course_id,
        booked_at=booking.booked_at,
        is_cancelled=booking.is_cancelled,
        cancelled_at=booking.cancelled_at,
        course=course_schema
    )


@router.delete("/{course_id}/book", response_model=BookingSchema)
def cancel_booking(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    取消预约
    """
    # 查找预约记录
    booking = db.query(BookingModel).filter(
        and_(
            BookingModel.course_id == course_id,
            BookingModel.user_id == current_user.id,
            BookingModel.is_cancelled == False
        )
    ).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到有效的预约记录"
        )
    
    # 检查课程时间
    course = db.query(CourseModel).filter(CourseModel.id == course_id).first()
    if course and course.start_time <= datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="课程已开始，无法取消预约"
        )
    
    # 取消预约
    booking.is_cancelled = True
    booking.cancelled_at = datetime.utcnow()
    db.commit()
    db.refresh(booking)
    
    # 返回预约信息
    current_bookings = db.query(BookingModel).filter(
        and_(
            BookingModel.course_id == course.id,
            BookingModel.is_cancelled == False
        )
    ).count()
    
    course_schema = CourseSchema(
        id=course.id,
        name=course.name,
        description=course.description,
        instructor=course.instructor,
        capacity=course.capacity,
        start_time=course.start_time,
        end_time=course.end_time,
        location=course.location,
        is_active=course.is_active,
        created_at=course.created_at,
        updated_at=course.updated_at,
        current_bookings=current_bookings,
        available_spots=course.capacity - current_bookings
    )
    
    return BookingSchema(
        id=booking.id,
        user_id=booking.user_id,
        course_id=booking.course_id,
        booked_at=booking.booked_at,
        is_cancelled=booking.is_cancelled,
        cancelled_at=booking.cancelled_at,
        course=course_schema
    )


@router.get("/bookings/my", response_model=BookingList)
def get_my_bookings(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=100, description="返回的记录数"),
    is_cancelled: Optional[bool] = Query(None, description="是否已取消"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取当前用户的预约列表
    """
    query = db.query(BookingModel).filter(BookingModel.user_id == current_user.id)
    
    if is_cancelled is not None:
        query = query.filter(BookingModel.is_cancelled == is_cancelled)
    
    query = query.order_by(BookingModel.booked_at.desc())
    
    total = query.count()
    bookings = query.offset(skip).limit(limit).all()
    
    booking_list = []
    for booking in bookings:
        course = db.query(CourseModel).filter(CourseModel.id == booking.course_id).first()
        if course:
            current_bookings = db.query(BookingModel).filter(
                and_(
                    BookingModel.course_id == course.id,
                    BookingModel.is_cancelled == False
                )
            ).count()
            
            course_schema = CourseSchema(
                id=course.id,
                name=course.name,
                description=course.description,
                instructor=course.instructor,
                capacity=course.capacity,
                start_time=course.start_time,
                end_time=course.end_time,
                location=course.location,
                is_active=course.is_active,
                created_at=course.created_at,
                updated_at=course.updated_at,
                current_bookings=current_bookings,
                available_spots=course.capacity - current_bookings
            )
            
            booking_schema = BookingSchema(
                id=booking.id,
                user_id=booking.user_id,
                course_id=booking.course_id,
                booked_at=booking.booked_at,
                is_cancelled=booking.is_cancelled,
                cancelled_at=booking.cancelled_at,
                course=course_schema
            )
            booking_list.append(booking_schema)
    
    return BookingList(bookings=booking_list, total=total)


@router.get("/{course_id}/bookings", response_model=BookingList)
def get_course_bookings(
    course_id: int,
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=100, description="返回的记录数"),
    is_cancelled: Optional[bool] = Query(None, description="是否已取消"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取课程的预约列表（需要管理员权限）
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    
    # 检查课程是否存在
    course = db.query(CourseModel).filter(CourseModel.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在"
        )
    
    query = db.query(BookingModel).filter(BookingModel.course_id == course_id)
    
    if is_cancelled is not None:
        query = query.filter(BookingModel.is_cancelled == is_cancelled)
    
    query = query.order_by(BookingModel.booked_at.desc())
    
    total = query.count()
    bookings = query.offset(skip).limit(limit).all()
    
    booking_list = []
    for booking in bookings:
        current_bookings = db.query(BookingModel).filter(
            and_(
                BookingModel.course_id == course.id,
                BookingModel.is_cancelled == False
            )
        ).count()
        
        course_schema = CourseSchema(
            id=course.id,
            name=course.name,
            description=course.description,
            instructor=course.instructor,
            capacity=course.capacity,
            start_time=course.start_time,
            end_time=course.end_time,
            location=course.location,
            is_active=course.is_active,
            created_at=course.created_at,
            updated_at=course.updated_at,
            current_bookings=current_bookings,
            available_spots=course.capacity - current_bookings
        )
        
        booking_schema = BookingSchema(
            id=booking.id,
            user_id=booking.user_id,
            course_id=booking.course_id,
            booked_at=booking.booked_at,
            is_cancelled=booking.is_cancelled,
            cancelled_at=booking.cancelled_at,
            course=course_schema
        )
        booking_list.append(booking_schema)
    
    return BookingList(bookings=booking_list, total=total)
