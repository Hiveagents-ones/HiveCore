from fastapi import APIRouter, Depends, HTTPException
from fastapi import status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Coach, Course
from ..schemas import CoachScheduleCreate, CoachScheduleResponse
from ..auth import get_current_admin_user
from datetime import datetime

router = APIRouter(
    prefix="/api/v1/coaches",
    tags=["coaches"],
)

@router.get("/{coach_id}", response_model=CoachScheduleResponse, status_code=status.HTTP_200_OK)


@router.get("/{coach_id}/schedule", response_model=List[CoachScheduleResponse], status_code=status.HTTP_200_OK)
def get_coach_schedule_by_id(
    coach_id: int,
    db: Session = Depends(get_db)
):
    """
    获取指定教练的排班信息

    参数:
        coach_id (int): 教练ID
        db (Session): 数据库会话

    返回:
        List[CoachScheduleResponse]: 指定教练的排班信息列表

    异常:
        HTTPException(404): 教练不存在
    """
    db_coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not db_coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    return db.query(Course).filter(Course.coach_id == coach_id).order_by(Course.start_time).all()
def get_coach_by_id(
    coach_id: int,
    db: Session = Depends(get_db)
):
    """
    获取指定教练的详细信息

    参数:
        coach_id (int): 教练ID
        db (Session): 数据库会话

    返回:
        CoachScheduleResponse: 教练详细信息

    异常:
        HTTPException(404): 教练不存在
    """
    db_coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not db_coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    return db_coach
@router.get("/", response_model=List[CoachScheduleResponse], status_code=status.HTTP_200_OK)
def get_all_coaches(db: Session = Depends(get_db)):
    """
    获取所有教练基本信息
    
    返回:
        List[CoachScheduleResponse]: 所有教练的基本信息列表
    """
    return db.query(Coach).all()
@router.get("/schedule", response_model=List[CoachScheduleResponse], status_code=status.HTTP_200_OK)
def get_coach_schedules(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    获取所有教练的排班信息
    
    参数:
        db (Session): 数据库会话
        current_user (dict): 当前管理员用户
        
    返回:
        List[CoachScheduleResponse]: 所有教练的排班信息列表
    """
    return db.query(Coach).all()

@router.post("/schedule", response_model=CoachScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_coach_schedule(
    schedule: CoachScheduleCreate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    创建教练排班
    
    参数:
        schedule (CoachScheduleCreate): 排班创建数据
        db (Session): 数据库会话
        current_user (dict): 当前管理员用户
        
    返回:
        CoachScheduleResponse: 创建的排班信息
        
    异常:
        HTTPException(404): 教练不存在
        HTTPException(400): 时间冲突
    """
    db_coach = db.query(Coach).filter(Coach.id == schedule.coach_id).first()
    if not db_coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    
    # 检查时间冲突
    conflicting_course = db.query(Course).filter(
        Course.coach_id == schedule.coach_id,
        Course.start_time < schedule.end_time,
        Course.end_time > schedule.start_time
    ).first()
    
    if conflicting_course:
        raise HTTPException(
            status_code=400, 
            detail="Coach already has a scheduled course during this time"
        )
    
    new_course = Course(
        name=schedule.course_name,
        coach_id=schedule.coach_id,
        start_time=schedule.start_time,
        end_time=schedule.end_time
    )
    
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    
    return new_course

@router.put("/schedule/{schedule_id}", response_model=CoachScheduleResponse, status_code=status.HTTP_200_OK)
def update_coach_schedule(
    schedule_id: int, 
    schedule: CoachScheduleCreate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    更新教练排班
    
    参数:
        schedule_id (int): 排班ID
        schedule (CoachScheduleCreate): 排班更新数据
        db (Session): 数据库会话
        current_user (dict): 当前管理员用户
        
    返回:
        CoachScheduleResponse: 更新后的排班信息
        
    异常:
        HTTPException(404): 排班或教练不存在
        HTTPException(400): 时间冲突
    """
    db_course = db.query(Course).filter(Course.id == schedule_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # 检查教练是否存在
    db_coach = db.query(Coach).filter(Coach.id == schedule.coach_id).first()
    if not db_coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    
    # 检查时间冲突（排除当前记录）
    conflicting_course = db.query(Course).filter(
        Course.coach_id == schedule.coach_id,
        Course.start_time < schedule.end_time,
        Course.end_time > schedule.start_time,
        Course.id != schedule_id
    ).first()
    
    if conflicting_course:
        raise HTTPException(
            status_code=400, 
            detail="Coach already has a scheduled course during this time"
        )
    
    db_course.name = schedule.course_name
    db_course.coach_id = schedule.coach_id
    db_course.start_time = schedule.start_time
    db_course.end_time = schedule.end_time
    
    db.commit()
    db.refresh(db_course)
    
    return db_course

@router.delete("/schedule/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_coach_schedule(
    schedule_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    删除教练排班
    
    参数:
        schedule_id (int): 排班ID
        db (Session): 数据库会话
        current_user (dict): 当前管理员用户
        
    返回:
        dict: 删除成功消息
        
    异常:
        HTTPException(404): 排班不存在
    """
    db_course = db.query(Course).filter(Course.id == schedule_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    db.delete(db_course)
    db.commit()
    
    return {"message": "Schedule deleted successfully"}

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
def get_coach_schedules(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    获取所有教练的排班信息

    参数:
        db (Session): 数据库会话
        current_user (dict): 当前管理员用户

    返回:
        List[CoachScheduleResponse]: 所有教练的排班信息列表
    """
    return db.query(Course).all()

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
@router.get("/schedule", response_model=List[CoachScheduleResponse], status_code=status.HTTP_200_OK)
def get_coach_schedules(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    获取所有教练的排班信息

    参数:
        db (Session): 数据库会话
        current_user (dict): 当前管理员用户

    返回:
        List[CoachScheduleResponse]: 所有教练的排班信息列表
    """
    return db.query(Course).order_by(Course.start_time).all()