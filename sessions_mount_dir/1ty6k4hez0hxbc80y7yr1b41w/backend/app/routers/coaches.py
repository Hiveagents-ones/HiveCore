from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..models.coach import Coach, CoachSchedule
from ..database import get_db

router = APIRouter(
    prefix="/api/v1/coaches",
    tags=["coaches"],
)


@router.get("/schedule", response_model=List[dict])
def get_coach_schedules(
    coach_id: int = None,
    start_time: datetime = None,
    end_time: datetime = None,
    db: Session = Depends(get_db),
):
    """
    获取教练排班列表
    
    Args:
        coach_id: 可选，教练ID
        start_time: 可选，开始时间(UTC)
        end_time: 可选，结束时间(UTC)
        
    Returns:
        List[dict]: 包含排班信息的字典列表，每个字典包含:
            - id: 排班ID
            - coach_id: 教练ID
            - start_time: 开始时间
            - end_time: 结束时间
            - status: 状态
            - coach_name: 教练姓名
    
    Raises:
        HTTPException: 如果查询参数无效
    """
    query = db.query(CoachSchedule)
    
    if coach_id:
        query = query.filter(CoachSchedule.coach_id == coach_id)
    
    if start_time:
        query = query.filter(CoachSchedule.start_time >= start_time)
    
    if end_time:
        query = query.filter(CoachSchedule.end_time <= end_time)
    
    schedules = query.all()
    return [
        {
            "id": schedule.id,
            "coach_id": schedule.coach_id,
            "start_time": schedule.start_time,
            "end_time": schedule.end_time,
            "status": schedule.status,
            "coach_name": schedule.coach.name,
        }
        for schedule in schedules
    ]


@router.post("/schedule", status_code=status.HTTP_201_CREATED)
def create_coach_schedule(
    schedule_data: dict,
    db: Session = Depends(get_db),
):
    """
    创建教练排班
    
    Args:
        schedule_data: 包含排班信息的字典，必须包含:
            - coach_id: 教练ID
            - start_time: 开始时间(UTC)
            - end_time: 结束时间(UTC)
            可选:
            - status: 排班状态(默认'available')
    
    Returns:
        dict: 创建成功的排班信息
        
    Raises:
        HTTPException 400: 缺少必要字段
        HTTPException 404: 教练不存在
        HTTPException 409: 时间冲突
    """
    required_fields = ["coach_id", "start_time", "end_time"]
    if not all(field in schedule_data for field in required_fields):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required fields: {required_fields}",
        )
    
    # 检查教练是否存在
    coach = db.query(Coach).filter(Coach.id == schedule_data["coach_id"]).first()
    if not coach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coach not found",
        )
    
    # 检查时间冲突
    existing_schedule = db.query(CoachSchedule).filter(
        CoachSchedule.coach_id == schedule_data["coach_id"],
        CoachSchedule.start_time < schedule_data["end_time"],
        CoachSchedule.end_time > schedule_data["start_time"],
    ).first()
    
    if existing_schedule:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Schedule conflict with existing schedule",
        )
    
    new_schedule = CoachSchedule(
        coach_id=schedule_data["coach_id"],
        start_time=schedule_data["start_time"],
        end_time=schedule_data["end_time"],
        status=schedule_data.get("status", "available"),
    )
    
    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)
    
    return {
        "id": new_schedule.id,
        "coach_id": new_schedule.coach_id,
        "start_time": new_schedule.start_time,
        "end_time": new_schedule.end_time,
        "status": new_schedule.status,
    }


@router.put("/schedule/{schedule_id}")
def update_coach_schedule(
    schedule_id: int,
    schedule_data: dict,
    db: Session = Depends(get_db),
):
    """
    更新教练排班
    
    Args:
        schedule_id: 要更新的排班ID
        schedule_data: 包含更新字段的字典，可以包含:
            - start_time: 新的开始时间
            - end_time: 新的结束时间
            - status: 新的状态
    
    Returns:
        dict: 更新后的排班信息
        
    Raises:
        HTTPException 404: 排班不存在
        HTTPException 409: 时间冲突
    """
    schedule = db.query(CoachSchedule).filter(CoachSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found",
        )
    
    # 更新字段
    if "start_time" in schedule_data:
        schedule.start_time = schedule_data["start_time"]
    if "end_time" in schedule_data:
        schedule.end_time = schedule_data["end_time"]
    if "status" in schedule_data:
        schedule.status = schedule_data["status"]
    
    # 检查时间冲突（排除自己）
    if "start_time" in schedule_data or "end_time" in schedule_data:
        conflicting_schedule = db.query(CoachSchedule).filter(
            CoachSchedule.coach_id == schedule.coach_id,
            CoachSchedule.id != schedule.id,
            CoachSchedule.start_time < schedule.end_time,
            CoachSchedule.end_time > schedule.start_time,
        ).first()
        
        if conflicting_schedule:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Schedule conflict with existing schedule",
            )
    
    schedule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(schedule)
    
    return {
        "id": schedule.id,
        "coach_id": schedule.coach_id,
        "start_time": schedule.start_time,
        "end_time": schedule.end_time,
        "status": schedule.status,
    }