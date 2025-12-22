from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional, Dict, Any

from .. import database, models, schemas
from ..core.auth import get_current_user

router = APIRouter(
    prefix="/api/v1/members",
    tags=["members"]
)

@router.post("/", response_model=schemas.Member, status_code=status.HTTP_201_CREATED)
def create_member(
    member: schemas.MemberCreate,
    db: Session = Depends(database.get_db),
    current_user: str = Depends(get_current_user)
):
    """创建新会员"""
    # 检查联系方式是否已存在
    db_member = db.query(models.Member).filter(models.Member.contact == member.contact).first()
    if db_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contact already registered"
        )
    
    db_member = models.Member(**member.dict())
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    
    # 记录审计日志
    audit_log = schemas.AuditLogCreate(
        action="CREATE",
        table_name="members",
        record_id=db_member.id,
        new_values=member.json(),
        user_id=current_user
    )
    db_audit = models.AuditLog(**audit_log.dict())
    db.add(db_audit)
    db.commit()
    
    return db_member

@router.get("/", response_model=List[schemas.Member])
def list_members(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = Query(None, description="搜索关键词（姓名或联系方式）"),
    status: Optional[models.MemberStatus] = Query(None, description="会员状态筛选"),
    level: Optional[str] = Query(None, description="会员等级筛选"),
    db: Session = Depends(database.get_db),
    current_user: str = Depends(get_current_user)
):
    """获取会员列表"""
    query = db.query(models.Member)
    
    # 搜索条件
    if search:
        query = query.filter(
            or_(
                models.Member.name.ilike(f"%{search}%"),
                models.Member.contact.ilike(f"%{search}%")
            )
        )
    
    # 状态筛选
    if status:
        query = query.filter(models.Member.status == status)
    
    # 等级筛选
    if level:
        query = query.filter(models.Member.level == level)
    
    members = query.offset(skip).limit(limit).all()
    return members

@router.get("/{member_id}", response_model=schemas.Member)
def get_member(
    member_id: int,
    db: Session = Depends(database.get_db),
    current_user: str = Depends(get_current_user)
):
    """获取单个会员信息"""
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    return member

@router.put("/{member_id}", response_model=schemas.Member)
def update_member(
    member_id: int,
    member_update: schemas.MemberUpdate,
    db: Session = Depends(database.get_db),
    current_user: str = Depends(get_current_user)
):
    """更新会员信息"""
    db_member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not db_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # 记录旧值用于审计
    old_values = schemas.Member.from_orm(db_member).json()
    
    # 更新字段
    update_data = member_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_member, field, value)
    
    db.commit()
    db.refresh(db_member)
    
    # 记录审计日志
    audit_log = schemas.AuditLogCreate(
        action="UPDATE",
        table_name="members",
        record_id=member_id,
        old_values=old_values,
        new_values=schemas.Member.from_orm(db_member).json(),
        user_id=current_user
    )
    db_audit = models.AuditLog(**audit_log.dict())
    db.add(db_audit)
    db.commit()
    
    return db_member

@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    member_id: int,
    db: Session = Depends(database.get_db),
    current_user: str = Depends(get_current_user)
):
    """删除会员"""
    db_member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not db_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # 记录旧值用于审计
    old_values = schemas.Member.from_orm(db_member).json()
    
    db.delete(db_member)
    db.commit()
    
    # 记录审计日志
    audit_log = schemas.AuditLogCreate(
        action="DELETE",
        table_name="members",
        record_id=member_id,
        old_values=old_values,
        user_id=current_user
    )
    db_audit = models.AuditLog(**audit_log.dict())
    db.add(db_audit)
    db.commit()
    
    return None

@router.post("/{member_id}/status", response_model=schemas.MemberStatusLog)
def change_member_status(
    member_id: int,
    status_change: schemas.MemberStatusLogBase,
    db: Session = Depends(database.get_db),
    current_user: str = Depends(get_current_user)
):
    """变更会员状态"""
    db_member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not db_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    old_status = db_member.status
    new_status = status_change.new_status
    
    if old_status == new_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New status is the same as current status"
        )
    
    # 更新会员状态
    db_member.status = new_status
    db.commit()
    
    # 记录状态变更日志
    status_log = schemas.MemberStatusLogCreate(
        member_id=member_id,
        old_status=old_status,
        new_status=new_status,
        changed_by=current_user
    )
    db_status_log = models.MemberStatusLog(**status_log.dict())
    db.add(db_status_log)
    db.commit()
    db.refresh(db_status_log)
    
    # 记录审计日志
    audit_log = schemas.AuditLogCreate(
        action="STATUS_CHANGE",
        table_name="members",
        record_id=member_id,
        old_values=f"status: {old_status.value}",
        new_values=f"status: {new_status.value}",
        user_id=current_user
    )
    db_audit = models.AuditLog(**audit_log.dict())
    db.add(db_audit)
    db.commit()
    
    return db_status_log

@router.get("/{member_id}/status_logs", response_model=List[schemas.MemberStatusLog])
@router.get("/{member_id}/entry_records", response_model=List[Dict[str, Any]])
def get_member_entry_records(
    member_id: int,
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    db: Session = Depends(database.get_db),
    current_user: str = Depends(get_current_user)
):
    """获取会员入场记录"""
    db_member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not db_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    query = db.query(models.EntryRecord).filter(models.EntryRecord.member_id == member_id)
    
    if start_date:
        query = query.filter(models.EntryRecord.entry_time >= start_date)
    if end_date:
        query = query.filter(models.EntryRecord.entry_time <= end_date)
    
    records = query.order_by(models.EntryRecord.entry_time.desc()).offset(skip).limit(limit).all()
    
    # 转换为字典格式以支持动态字段
    return [record.__dict__ for record in records]


def get_member_status_logs(
    member_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(database.get_db),
    current_user: str = Depends(get_current_user)
):
    """获取会员状态变更历史"""
    db_member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not db_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    logs = db.query(models.MemberStatusLog).filter(
        models.MemberStatusLog.member_id == member_id
    ).order_by(models.MemberStatusLog.changed_at.desc()).offset(skip).limit(limit).all()
    
    return logs

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
@router.post("/", response_model=schemas.Member, status_code=status.HTTP_201_CREATED)
def create_member(
    member: schemas.MemberCreate,
    db: Session = Depends(database.get_db),
    current_user: str = Depends(get_current_user)
):
    """创建新会员"""
    # 检查联系方式是否已存在
    db_member = db.query(models.Member).filter(models.Member.contact == member.contact).first()
    if db_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contact already registered"
        )

    # 处理动态字段
    member_data = member.dict()
    dynamic_fields = member_data.pop('dynamic_fields', {})
    
    db_member = models.Member(**member_data)
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    
    # 保存动态字段
    if dynamic_fields:
        for field_name, field_value in dynamic_fields.items():
            dynamic_field = models.MemberDynamicField(
                member_id=db_member.id,
                field_name=field_name,
                field_value=field_value
            )
            db.add(dynamic_field)
        db.commit()

    # 记录审计日志
    audit_log = schemas.AuditLogCreate(
        action="CREATE",
        table_name="members",
        record_id=db_member.id,
        new_values=member.json(),
        user_id=current_user
    )
    db_audit = models.AuditLog(**audit_log.dict())
    db.add(db_audit)
    db.commit()

    return db_member

# [AUTO-APPENDED] Failed to replace, adding new code:
@router.get("/", response_model=List[schemas.Member])
def list_members(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = Query(None, description="搜索关键词（姓名或联系方式）"),
    status: Optional[models.MemberStatus] = Query(None, description="会员状态筛选"),
    level: Optional[str] = Query(None, description="会员等级筛选"),
    db: Session = Depends(database.get_db),
    current_user: str = Depends(get_current_user)
):
    """获取会员列表"""
    # 使用join优化查询
    query = db.query(models.Member).options(
        joinedload(models.Member.dynamic_fields)
    )

    # 搜索条件
    if search:
        query = query.filter(
            or_(
                models.Member.name.ilike(f"%{search}%"),
                models.Member.contact.ilike(f"%{search}%")
            )
        )

    # 状态筛选
    if status:
        query = query.filter(models.Member.status == status)

    # 等级筛选
    if level:
        query = query.filter(models.Member.level == level)

    members = query.offset(skip).limit(limit).all()
    return members

# [AUTO-APPENDED] Failed to replace, adding new code:
@router.put("/{member_id}", response_model=schemas.Member)
def update_member(
    member_id: int,
    member_update: schemas.MemberUpdate,
    db: Session = Depends(database.get_db),
    current_user: str = Depends(get_current_user)
):
    """更新会员信息"""
    db_member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not db_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    # 记录旧值用于审计
    old_values = schemas.Member.from_orm(db_member).json()

    # 更新字段
    update_data = member_update.dict(exclude_unset=True)
    dynamic_fields = update_data.pop('dynamic_fields', None)
    
    for field, value in update_data.items():
        setattr(db_member, field, value)

    # 处理动态字段更新
    if dynamic_fields is not None:
        # 删除旧的动态字段
        db.query(models.MemberDynamicField).filter(
            models.MemberDynamicField.member_id == member_id
        ).delete()
        
        # 添加新的动态字段
        for field_name, field_value in dynamic_fields.items():
            dynamic_field = models.MemberDynamicField(
                member_id=member_id,
                field_name=field_name,
                field_value=field_value
            )
            db.add(dynamic_field)

    db.commit()
    db.refresh(db_member)

    # 记录审计日志
    audit_log = schemas.AuditLogCreate(
        action="UPDATE",
        table_name="members",
        record_id=member_id,
        old_values=old_values,
        new_values=schemas.Member.from_orm(db_member).json(),
        user_id=current_user
    )
    db_audit = models.AuditLog(**audit_log.dict())
    db.add(db_audit)
    db.commit()

    return db_member