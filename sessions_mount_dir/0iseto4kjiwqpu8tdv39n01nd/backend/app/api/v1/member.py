from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.models.member import Member as MemberModel
from app.models.user import User
from app.schemas.member import (
    Member,
    MemberCreate,
    MemberUpdate,
    MemberList,
    MemberWithAuditLogs,
    AuditLogCreate,
)
from app.services.audit import AuditService
import csv
import io
from datetime import datetime

router = APIRouter()


@router.post("/", response_model=Member, status_code=status.HTTP_201_CREATED)
def create_member(
    member: MemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建新会员
    """
    # 检查邮箱是否已存在
    existing_member = db.query(MemberModel).filter(MemberModel.email == member.email).first()
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册",
        )

    db_member = MemberModel(**member.dict())
    db.add(db_member)
    db.commit()
    db.refresh(db_member)

    # 记录审计日志
    audit_service = AuditService(db)
    audit_service.log_action(
        user_id=current_user.id,
        action="create",
        resource_type="member",
        resource_id=db_member.id,
        details={"member_data": member.dict()},
    )

    return db_member


@router.get("/", response_model=MemberList)
def list_members(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(10, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    membership_level: Optional[str] = Query(None, description="会员等级筛选"),
    is_active: Optional[bool] = Query(None, description="会员状态筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取会员列表
    """
    query = db.query(MemberModel)

    # 应用筛选条件
    if search:
        query = query.filter(
            (MemberModel.name.ilike(f"%{search}%")) |
            (MemberModel.email.ilike(f"%{search}%")) |
            (MemberModel.phone.ilike(f"%{search}%"))
        )

    if membership_level:
        query = query.filter(MemberModel.membership_level == membership_level)

    if is_active is not None:
        query = query.filter(MemberModel.is_active == is_active)

    # 计算总数
    total = query.count()

    # 应用分页
    members = query.offset((page - 1) * per_page).limit(per_page).all()

    return MemberList(
        members=members,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{member_id}", response_model=MemberWithAuditLogs)
def get_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取单个会员详情（包含审计日志）
    """
    member = db.query(MemberModel).filter(MemberModel.id == member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会员不存在",
        )

    # 获取审计日志
    from app.models.audit import AuditLog as AuditLogModel
    audit_logs = (
        db.query(AuditLogModel)
        .filter(AuditLogModel.resource_id == member_id)
        .filter(AuditLogModel.resource_type == "member")
        .order_by(AuditLogModel.timestamp.desc())
        .all()
    )

    return MemberWithAuditLogs(
        **member.__dict__,
        audit_logs=audit_logs,
    )


@router.put("/{member_id}", response_model=Member)
def update_member(
    member_id: int,
    member_update: MemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新会员信息
    """
    db_member = db.query(MemberModel).filter(MemberModel.id == member_id).first()
    if not db_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会员不存在",
        )

    # 如果更新邮箱，检查是否已存在
    if member_update.email and member_update.email != db_member.email:
        existing_member = db.query(MemberModel).filter(MemberModel.email == member_update.email).first()
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该邮箱已被注册",
            )

    # 记录更新前的值
    old_values = db_member.__dict__.copy()
    old_values.pop('_sa_instance_state', None)

    # 更新会员信息
    update_data = member_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_member, field, value)

    db_member.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_member)

    # 记录审计日志
    audit_service = AuditService(db)
    audit_service.log_action(
        user_id=current_user.id,
        action="update",
        resource_type="member",
        resource_id=db_member.id,
        details={
            "old_values": old_values,
            "new_values": update_data,
        },
    )

    return db_member


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除会员
    """
    db_member = db.query(MemberModel).filter(MemberModel.id == member_id).first()
    if not db_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会员不存在",
        )

    # 记录删除前的值
    old_values = db_member.__dict__.copy()
    old_values.pop('_sa_instance_state', None)

    db.delete(db_member)
    db.commit()

    # 记录审计日志
    audit_service = AuditService(db)
    audit_service.log_action(
        user_id=current_user.id,
        action="delete",
        resource_type="member",
        resource_id=member_id,
        details={"deleted_member": old_values},
    )


@router.post("/import", response_model=MemberList)
def import_members(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    批量导入会员
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只支持CSV文件",
        )

    # 读取CSV文件内容
    contents = file.file.read()
    file.file.close()

    # 解析CSV
    csv_reader = csv.DictReader(io.StringIO(contents.decode('utf-8')))
    imported_members = []
    errors = []

    for row_num, row in enumerate(csv_reader, start=2):
        try:
            # 验证必填字段
            if not row.get('name') or not row.get('email'):
                errors.append(f"第{row_num}行: 姓名和邮箱为必填字段")
                continue

            # 检查邮箱是否已存在
            if db.query(MemberModel).filter(MemberModel.email == row['email']).first():
                errors.append(f"第{row_num}行: 邮箱 {row['email']} 已存在")
                continue

            # 创建会员
            member_data = {
                'name': row['name'],
                'email': row['email'],
                'phone': row.get('phone'),
                'membership_level': row.get('membership_level', 'basic'),
                'remaining_membership': int(row.get('remaining_membership', 0)),
                'is_active': row.get('is_active', 'true').lower() == 'true',
            }

            db_member = MemberModel(**member_data)
            db.add(db_member)
            imported_members.append(db_member)

        except Exception as e:
            errors.append(f"第{row_num}行: {str(e)}")

    # 提交所有成功的导入
    if imported_members:
        db.commit()
        for member in imported_members:
            db.refresh(member)

        # 记录批量导入审计日志
        audit_service = AuditService(db)
        audit_service.log_action(
            user_id=current_user.id,
            action="bulk_import",
            resource_type="member",
            details={
                "imported_count": len(imported_members),
                "errors": errors,
            },
        )

    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": errors, "imported_count": len(imported_members)},
        )

    return MemberList(
        members=imported_members,
        total=len(imported_members),
        page=1,
        per_page=len(imported_members),
    )


@router.post("/{member_id}/audit-log", response_model=dict)
def add_audit_log(
    member_id: int,
    audit_log: AuditLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    为会员添加审计日志
    """
    # 验证会员是否存在
    member = db.query(MemberModel).filter(MemberModel.id == member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会员不存在",
        )

    # 创建审计日志
    from app.models.audit import AuditLog as AuditLogModel
    db_audit_log = AuditLogModel(
        member_id=member_id,
        action=audit_log.action,
        old_values=audit_log.old_values,
        new_values=audit_log.new_values,
        created_at=datetime.utcnow(),
    )
    db.add(db_audit_log)
    db.commit()
    db.refresh(db_audit_log)

    return {"message": "审计日志添加成功", "audit_log_id": db_audit_log.id}
