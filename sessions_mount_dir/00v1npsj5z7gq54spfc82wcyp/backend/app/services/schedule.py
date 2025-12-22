from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from fastapi import Depends
from fastapi.encoders import jsonable_encoder

from app.schemas.coach import CoachScheduleCreate, CoachScheduleConflict
from app.database import models


def check_schedule_conflict(
    db: Session,
    coach_id: int,
    new_schedule: CoachScheduleCreate,
    raise_exception: bool = False
) -> Optional[CoachScheduleConflict]:
    """
    检查教练排班冲突，支持批量检测
    
    参数:
        db: 数据库会话
        coach_id: 教练ID
        new_schedule: 新排班信息
        raise_exception: 是否抛出异常(默认为False)
    
    返回:
        如果有冲突返回冲突信息，否则返回None
    
    异常:
        HTTPException: 如果raise_exception为True且检测到冲突
    """
    """
    检查教练排班冲突

    参数:
        db: 数据库会话
        coach_id: 教练ID
        new_schedule: 新排班信息
        raise_exception: 是否抛出异常(默认为False)

    返回:
        如果有冲突返回冲突信息，否则返回None

    异常:
        HTTPException: 如果raise_exception为True且检测到冲突
    """
    """
    检查教练排班冲突
    
    参数:
        db: 数据库会话
        coach_id: 教练ID
        new_schedule: 新排班信息
        
    返回:
        如果有冲突返回冲突信息，否则返回None
    """
    # 获取教练现有的排班
    existing_schedules = db.query(models.CoachSchedule).filter(
        models.CoachSchedule.coach_id == coach_id
    ).all()
    
    # 将新排班的时间转换为datetime对象
    new_start = datetime.fromisoformat(new_schedule.start_time)
    new_end = datetime.fromisoformat(new_schedule.end_time)
    
    # 检查每个现有排班是否有冲突
    for schedule in existing_schedules:
        existing_start = datetime.fromisoformat(schedule.start_time)
        existing_end = datetime.fromisoformat(schedule.end_time)
        
        # 检查时间重叠
        if not (new_end <= existing_start or new_start >= existing_end):
            if raise_exception:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=jsonable_encoder({
                        "message": "Schedule conflict detected",
                        "conflict": {
                            "existing_schedule_id": schedule.id,
                            "existing_start_time": schedule.start_time,
                            "existing_end_time": schedule.end_time,
                            "new_start_time": new_schedule.start_time,
                            "new_end_time": new_schedule.end_time
                        }
                    })
                )
            return CoachScheduleConflict(
                existing_schedule_id=schedule.id,
                existing_start_time=schedule.start_time,
                existing_end_time=schedule.end_time,
                new_start_time=new_schedule.start_time,
                new_end_time=new_schedule.end_time
            )
    
    return None


def get_coach_schedules(
    db: Session,
    coach_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[models.CoachSchedule]:
    """
    获取教练排班列表，支持分页和日期范围筛选
    
    参数:
        db: 数据库会话
        coach_id: 教练ID
        start_date: 开始日期(可选)
        end_date: 结束日期(可选)
    
    返回:
        排班列表
    
    异常:
        HTTPException: 如果日期范围无效
    """
    """
    获取教练排班列表，可按日期范围筛选

    参数:
        db: 数据库会话
        coach_id: 教练ID
        start_date: 开始日期(可选)
        end_date: 结束日期(可选)

    返回:
        排班列表

    异常:
        HTTPException: 如果日期范围无效
    """
    # 验证日期范围
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date cannot be after end date"
        )
    """
    获取教练排班列表，可按日期范围筛选
    
    参数:
        db: 数据库会话
        coach_id: 教练ID
        start_date: 开始日期(可选)
        end_date: 结束日期(可选)
        
    返回:
        排班列表
    """
    query = db.query(models.CoachSchedule).filter(
        models.CoachSchedule.coach_id == coach_id
    )
    
    if start_date and end_date:
        query = query.filter(
            models.CoachSchedule.start_time >= start_date,
            models.CoachSchedule.end_time <= end_date
        )
    
    return query.order_by(models.CoachSchedule.start_time).all()


def create_coach_schedule(
    db: Session,
    coach_id: int,
    schedule: CoachScheduleCreate
) -> models.CoachSchedule:
    """
    创建教练排班，自动检测冲突
    
    参数:
        db: 数据库会话
        coach_id: 教练ID
        schedule: 排班信息
    
    返回:
        创建的排班记录
    
    异常:
        HTTPException: 如果排班时间冲突
    """
    """
    创建教练排班

    参数:
        db: 数据库会话
        coach_id: 教练ID
        schedule: 排班信息

    返回:
        创建的排班记录

    异常:
        HTTPException: 如果排班时间冲突
    """
    # 首先检查排班冲突，如果冲突则抛出异常
    check_schedule_conflict(db, coach_id, schedule, raise_exception=True)
    """
    创建教练排班
    
    参数:
        db: 数据库会话
        coach_id: 教练ID
        schedule: 排班信息
        
    返回:
        创建的排班记录
    """
    db_schedule = models.CoachSchedule(
        coach_id=coach_id,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        course_id=schedule.course_id
    )
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule


def delete_coach_schedule(
    db: Session,
    schedule_id: int
) -> bool:
    """
    删除教练排班
    
    参数:
        db: 数据库会话
        schedule_id: 排班ID
    
    返回:
        是否删除成功
    """
    
    """
    删除教练排班
    
    参数:
        db: 数据库会话
        schedule_id: 排班ID
        
    返回:
        是否删除成功
    """
    schedule = db.query(models.CoachSchedule).filter(
        models.CoachSchedule.id == schedule_id
    ).first()
    
    if not schedule:
        return False
    
    db.delete(schedule)
    db.commit()
    return True