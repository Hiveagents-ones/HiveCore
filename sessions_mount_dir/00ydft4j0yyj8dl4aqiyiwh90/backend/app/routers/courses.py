from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Course
from ..schemas import CourseSchema, CourseCreate

router = APIRouter(
    prefix="/api/v1/courses",
    tags=["courses"]
)

@router.get("/", response_model=List[CourseSchema])
def get_courses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    获取课程列表
    
    Args:
        skip: 跳过的记录数
        limit: 返回的最大记录数
        db: 数据库会话
        
    Returns:
        课程列表
    """
    courses = db.query(Course).offset(skip).limit(limit).all()
    return courses

@router.post("/", response_model=CourseSchema)
def create_course(course: CourseCreate, db: Session = Depends(get_db)):
    """
    创建新课程
    
    Args:
        course: 课程创建数据
        db: 数据库会话
        
    Returns:
        创建的课程
    """
    db_course = Course(**course.dict())
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course

@router.get("/{course_id}", response_model=CourseSchema)
def get_course(course_id: int, db: Session = Depends(get_db)):
    """
    获取单个课程详情
    
    Args:
        course_id: 课程ID
        db: 数据库会话
        
    Returns:
        课程详情
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@router.put("/{course_id}", response_model=CourseSchema)
def update_course(course_id: int, course: CourseCreate, db: Session = Depends(get_db)):
    """
    更新课程信息
    
    Args:
        course_id: 课程ID
        course: 课程更新数据
        db: 数据库会话
        
    Returns:
        更新后的课程
    """
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    for key, value in course.dict().items():
        setattr(db_course, key, value)
    
    db.commit()
    db.refresh(db_course)
    return db_course

@router.delete("/{course_id}")
def delete_course(course_id: int, db: Session = Depends(get_db)):
    """
    删除课程
    
    Args:
        course_id: 课程ID
        db: 数据库会话
        
    Returns:
        操作结果
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    db.delete(course)
    db.commit()
    return {"message": "Course deleted successfully"}