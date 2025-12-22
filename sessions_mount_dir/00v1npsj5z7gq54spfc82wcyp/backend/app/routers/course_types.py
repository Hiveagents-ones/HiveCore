from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import Request
from sqlalchemy.orm import Session
from typing import List

from ..models.course_type import CourseType
from ..database import get_db
from ..schemas.course_type import CourseTypeCreate, CourseTypeUpdate
from ..schemas.course_type import CourseTypeConfig
from ..middlewares.versioning import VersioningMiddleware

router = APIRouter(
    prefix="/api/v1/course-types",
    tags=["course-types"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[CourseType])
def list_course_types(
    request: Request,
    db: Session = Depends(get_db)
):

    """获取所有课程类型"""
    return db.query(CourseType).filter(CourseType.is_active == True).all()


@router.get("/{course_type_id}", response_model=CourseType)
@router.get("/{course_type_id}/availability", response_model=bool)
def check_course_type_availability(
    request: Request,
    course_type_id: int, 
    db: Session = Depends(get_db)
):
    """检查课程类型是否可预约"""
    course_type = db.query(CourseType).filter(CourseType.id == course_type_id).first()
    if not course_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course type not found"
        )
    return course_type.allow_booking
def get_course_type(
    request: Request,
    course_type_id: int, 
    db: Session = Depends(get_db)
):
    """获取特定课程类型详情"""
    course_type = db.query(CourseType).filter(CourseType.id == course_type_id).first()
    if not course_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course type not found"
        )
    return course_type


@router.post("/", response_model=CourseType, status_code=status.HTTP_201_CREATED)
def create_course_type(
    request: Request,
    course_type: CourseTypeCreate, 
    db: Session = Depends(get_db)
):
    """创建新课程类型"""
    db.add(course_type)
    db.commit()
    db.refresh(course_type)
    return course_type


@router.put("/{course_type_id}", response_model=CourseType)
def update_course_type(
    request: Request,
    course_type_id: int, 
    updated_course_type: CourseTypeUpdate, 
    db: Session = Depends(get_db)
):
    """更新课程类型信息"""
    course_type = db.query(CourseType).filter(CourseType.id == course_type_id).first()
    if not course_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course type not found"
        )
    
    for key, value in updated_course_type.__dict__.items():
        if key != "_sa_instance_state":
            setattr(course_type, key, value)
    
    db.commit()
    db.refresh(course_type)
    return course_type


@router.delete("/{course_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course_type(
    request: Request,
    course_type_id: int, 
    db: Session = Depends(get_db)
):
    """删除课程类型（软删除）"""
    course_type = db.query(CourseType).filter(CourseType.id == course_type_id).first()
    if not course_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course type not found"
        )

    course_type.is_active = False
    db.commit()
    return None


@router.put("/{course_type_id}/config", response_model=CourseType)
def update_course_type_config(
    request: Request,
    course_type_id: int, 
    config: CourseTypeConfig,
    db: Session = Depends(get_db)
):
    """更新课程类型配置"""
    course_type = db.query(CourseType).filter(CourseType.id == course_type_id).first()
    if not course_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course type not found"
        )

    # 更新可配置项
    course_type.allow_booking = config.allow_booking
    course_type.booking_window_days = config.booking_window_days
    course_type.min_booking_hours = config.min_booking_hours
    course_type.cancellation_hours = config.cancellation_hours
    course_type.refund_policy = config.refund_policy
    course_type.max_capacity = config.max_capacity
    course_type.price = config.price

    db.commit()
    db.refresh(course_type)
    return course_type
def update_course_type_config(
    request: Request,
    course_type_id: int, 
    config: CourseTypeConfig,
    db: Session = Depends(get_db)
):
    """更新课程类型配置"""
    course_type = db.query(CourseType).filter(CourseType.id == course_type_id).first()
    if not course_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course type not found"
        )

    # 更新可配置项
    course_type.allow_booking = config.allow_booking
    course_type.booking_window_days = config.booking_window_days
    course_type.min_booking_hours = config.min_booking_hours
    course_type.cancellation_hours = config.cancellation_hours
    course_type.refund_policy = config.refund_policy
    course_type.max_capacity = config.max_capacity
    course_type.price = config.price

    db.commit()
    db.refresh(course_type)
    return course_type
def delete_course_type(
    request: Request,
    course_type_id: int, 
    db: Session = Depends(get_db)
):
    """删除课程类型（软删除）"""
    course_type = db.query(CourseType).filter(CourseType.id == course_type_id).first()
    if not course_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course type not found"
        )
    
    course_type.is_active = False
    db.commit()
    return None