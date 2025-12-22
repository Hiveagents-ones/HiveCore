from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models import Activity, Merchant
from ..schemas import (
    ActivityCreate,
    ActivityUpdate,
    ActivityResponse,
    Merchant as MerchantSchema
)
from ..core.deps import get_current_active_merchant, get_db
from ..core.database import get_db
from ..core.config import settings
from ..core.audit import log_activity_change

router = APIRouter(prefix="/api/activities", tags=["activities"])


@router.post("/", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def create_activity(
    activity: ActivityCreate,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_active_merchant)
):
    """创建新活动"""
    # 验证商家权限
    if activity.merchant_id != current_merchant.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create activity for this merchant"
        )
    
    # 检查时间冲突
    conflict = db.query(Activity).filter(
        and_(
            Activity.merchant_id == current_merchant.id,
            Activity.status.in_(['draft', 'published']),
            Activity.start_time <= activity.end_time,
            Activity.end_time >= activity.start_time
        )
    ).first()
    
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Activity time conflicts with existing activity"
        )
    
    db_activity = Activity(**activity.dict())
    db.add(db_activity)
    db.commit()
    db.refresh(db_activity)
    
    # 记录审计日志
    log_activity_change(
        db=db,
        activity_id=db_activity.id,
        merchant_id=current_merchant.id,
        action="create",
        old_values=None,
        new_values=activity.dict()
    )
    
    return db_activity


@router.get("/", response_model=List[ActivityResponse])
def list_activities(
    status: Optional[str] = Query(None, regex="^(draft|published|cancelled|completed)$"),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_active_merchant)
):
    """获取当前商家的活动列表"""
    query = db.query(Activity).filter(Activity.merchant_id == current_merchant.id)
    
    if status:
        query = query.filter(Activity.status == status)
    if is_active is not None:
        query = query.filter(Activity.is_active == is_active)
    
    activities = query.offset(skip).limit(limit).all()
    return activities


@router.get("/{activity_id}", response_model=ActivityResponse)
def get_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_active_merchant)
):
    """获取活动详情"""
    activity = db.query(Activity).filter(
        and_(
            Activity.id == activity_id,
            Activity.merchant_id == current_merchant.id
        )
    ).first()
    
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found"
        )
    
    return activity


@router.put("/{activity_id}", response_model=ActivityResponse)
def update_activity(
    activity_id: int,
    activity_update: ActivityUpdate,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_active_merchant)
):
    """更新活动信息"""
    db_activity = db.query(Activity).filter(
        and_(
            Activity.id == activity_id,
            Activity.merchant_id == current_merchant.id
        )
    ).first()
    
    if not db_activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found"
        )
    
    # 检查活动状态是否允许修改
    if db_activity.status in ['cancelled', 'completed']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update cancelled or completed activity"
        )
    
    # 保存旧值用于审计
    old_values = {
        "name": db_activity.name,
        "description": db_activity.description,
        "start_time": db_activity.start_time,
        "end_time": db_activity.end_time,
        "location": db_activity.location,
        "rules": db_activity.rules,
        "rewards": db_activity.rewards,
        "status": db_activity.status,
        "is_active": db_activity.is_active
    }
    
    # 更新字段
    update_data = activity_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_activity, field, value)
    
    # 增加版本号
    db_activity.version += 1
    
    # 检查时间冲突
    if 'start_time' in update_data or 'end_time' in update_data:
        conflict = db.query(Activity).filter(
            and_(
                Activity.merchant_id == current_merchant.id,
                Activity.id != activity_id,
                Activity.status.in_(['draft', 'published']),
                Activity.start_time <= db_activity.end_time,
                Activity.end_time >= db_activity.start_time
            )
        ).first()
        
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Updated activity time conflicts with existing activity"
            )
    
    db.commit()
    db.refresh(db_activity)
    
    # 记录审计日志
    log_activity_change(
        db=db,
        activity_id=activity_id,
        merchant_id=current_merchant.id,
        action="update",
        old_values=old_values,
        new_values=update_data
    )
    
    return db_activity


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_active_merchant)
):
    """删除活动"""
    db_activity = db.query(Activity).filter(
        and_(
            Activity.id == activity_id,
            Activity.merchant_id == current_merchant.id
        )
    ).first()
    
    if not db_activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found"
        )
    
    # 检查活动状态是否允许删除
    if db_activity.status == 'published':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete published activity. Cancel it first."
        )
    
    # 保存旧值用于审计
    old_values = {
        "name": db_activity.name,
        "description": db_activity.description,
        "start_time": db_activity.start_time,
        "end_time": db_activity.end_time,
        "location": db_activity.location,
        "rules": db_activity.rules,
        "rewards": db_activity.rewards,
        "status": db_activity.status,
        "is_active": db_activity.is_active
    }
    
    db.delete(db_activity)
    db.commit()
    
    # 记录审计日志
    log_activity_change(
        db=db,
        activity_id=activity_id,
        merchant_id=current_merchant.id,
        action="delete",
        old_values=old_values,
        new_values=None
    )


@router.patch("/{activity_id}/publish", response_model=ActivityResponse)
def publish_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_active_merchant)
):
    """发布活动"""
    db_activity = db.query(Activity).filter(
        and_(
            Activity.id == activity_id,
            Activity.merchant_id == current_merchant.id
        )
    ).first()
    
    if not db_activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found"
        )
    
    if db_activity.status != 'draft':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft activities can be published"
        )
    
    # 检查活动时间是否在未来
    if db_activity.start_time <= datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Activity start time must be in the future"
        )
    
    old_status = db_activity.status
    db_activity.status = 'published'
    db_activity.version += 1
    db.commit()
    db.refresh(db_activity)
    
    # 记录审计日志
    log_activity_change(
        db=db,
        activity_id=activity_id,
        merchant_id=current_merchant.id,
        action="publish",
        old_values={"status": old_status},
        new_values={"status": "published"}
    )
    
    return db_activity


@router.patch("/{activity_id}/cancel", response_model=ActivityResponse)
def cancel_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_active_merchant)
):
    """取消活动"""
    db_activity = db.query(Activity).filter(
        and_(
            Activity.id == activity_id,
            Activity.merchant_id == current_merchant.id
        )
    ).first()
    
    if not db_activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found"
        )
    
    if db_activity.status not in ['draft', 'published']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft or published activities can be cancelled"
        )
    
    old_status = db_activity.status
    db_activity.status = 'cancelled'
    db_activity.version += 1
    db.commit()
    db.refresh(db_activity)
    
    # 记录审计日志
    log_activity_change(
        db=db,
        activity_id=activity_id,
        merchant_id=current_merchant.id,
        action="cancel",
        old_values={"status": old_status},
        new_values={"status": "cancelled"}
    )
    
    return db_activity


@router.patch("/{activity_id}/complete", response_model=ActivityResponse)
def complete_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_active_merchant)
):
    """完成活动"""
    db_activity = db.query(Activity).filter(
        and_(
            Activity.id == activity_id,
            Activity.merchant_id == current_merchant.id
        )
    ).first()
    
    if not db_activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found"
        )
    
    if db_activity.status != 'published':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only published activities can be completed"
        )
    
    if db_activity.end_time > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot complete activity before its end time"
        )
    
    old_status = db_activity.status
    db_activity.status = 'completed'
    db_activity.version += 1
    db.commit()
    db.refresh(db_activity)
    
    # 记录审计日志
    log_activity_change(
        db=db,
        activity_id=activity_id,
        merchant_id=current_merchant.id,
        action="complete",
        old_values={"status": old_status},
        new_values={"status": "completed"}
    )
    
    return db_activity
