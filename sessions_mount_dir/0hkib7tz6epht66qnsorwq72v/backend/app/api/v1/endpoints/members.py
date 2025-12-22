from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ....crud import member as member_crud
from ....schemas.member import (
    Member,
    MemberCreate,
    MemberListResponse,
    MemberResponse,
    MemberUpdate,
)
from ....core.config import get_db
from ....core.rbac import require_permission
from ....core.audit import audit_action
from ....models.permission import User


router = APIRouter()


@router.post("/", response_model=MemberResponse, summary="创建新会员")
@require_permission("member:create")
@audit_action(action="CREATE_MEMBER", resource_type="MEMBER", get_new_values=lambda member, **kwargs: member.dict())
def create_member(member: MemberCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    创建一个新的会员档案。
    - **name**: 会员姓名
    - **phone**: 手机号码
    - **email**: 电子邮箱 (可选)
    - **level**: 会员等级 (默认: 普通会员)
    - **points**: 会员积分 (默认: 0)
    - **remaining_membership**: 剩余会籍(月) (默认: 0)
    - **is_active**: 是否激活 (默认: True)
    - **notes**: 备注信息 (可选)
    """
    db_member = member_crud.get_member_by_phone(db, phone=member.phone)
    if db_member:
        raise HTTPException(status_code=400, detail="手机号已被注册")
    return member_crud.create_member(db=db, member=member)


@router.get("/", response_model=MemberListResponse, summary="获取会员列表")
@require_permission("member:read")
def read_members(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=200, description="返回的记录数"),
    level: Optional[str] = Query(None, description="按会员等级筛选"),
    is_active: Optional[bool] = Query(None, description="按激活状态筛选"),
):
    """
    获取会员列表，支持分页和筛选。
    - **skip**: 跳过的记录数
    - **limit**: 返回的记录数 (最大200)
    - **level**: 筛选特定等级的会员
    - **is_active**: 筛选激活或未激活的会员
    """
    members = member_crud.get_members(
        db, skip=skip, limit=limit, level=level, is_active=is_active
    )
    # TODO: Implement total count in crud for accurate pagination
    total = len(members) # Simplified for now
    page = (skip // limit) + 1
    size = limit
    return {"members": members, "total": total, "page": page, "size": size}


@router.get("/{member_id}", response_model=MemberResponse, summary="获取单个会员")
@require_permission("member:read")
def read_member(member_id: int, db: Session = Depends(get_db)):
    """
    根据ID获取单个会员的详细信息。
    - **member_id**: 会员的唯一标识符
    """
    db_member = member_crud.get_member(db, member_id=member_id)
    if db_member is None:
        raise HTTPException(status_code=404, detail="会员未找到")
    return db_member


@router.put("/{member_id}", response_model=MemberResponse, summary="更新会员信息")
@require_permission("member:update")
@audit_action(action="UPDATE_MEMBER", resource_type="MEMBER", resource_id=lambda member_id, **kwargs: str(member_id), get_old_values=lambda member_id, db, **kwargs: member_crud.get_member(db, member_id).dict(), get_new_values=lambda member, **kwargs: member.dict(exclude_unset=True))
def update_member(
    member_id: int, member: MemberUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    更新指定ID的会员信息。只需提供需要更新的字段。
    - **member_id**: 会员的唯一标识符
    - **member**: 包含更新字段的请求体
    """
    db_member = member_crud.update_member(db, member_id=member_id, member=member)
    if db_member is None:
        raise HTTPException(status_code=404, detail="会员未找到")
    return db_member


@router.delete("/{member_id}", summary="删除会员")
@require_permission("member:delete")
@audit_action(action="DELETE_MEMBER", resource_type="MEMBER", resource_id=lambda member_id, **kwargs: str(member_id))
def delete_member(member_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    根据ID删除一个会员。此操作不可逆。
    - **member_id**: 会员的唯一标识符
    """
    success = member_crud.delete_member(db, member_id=member_id)
    if not success:
        raise HTTPException(status_code=404, detail="会员未找到")
    return {"detail": "会员已成功删除"}


@router.post("/{member_id}/deactivate", response_model=MemberResponse, summary="停用会员")
@require_permission("member:update")
@audit_action(action="DEACTIVATE_MEMBER", resource_type="MEMBER", resource_id=lambda member_id, **kwargs: str(member_id))
def deactivate_member_endpoint(member_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    停用指定ID的会员。停用后会员无法登录或享受会员权益。
    - **member_id**: 会员的唯一标识符
    """
    db_member = member_crud.deactivate_member(db, member_id=member_id)
    if db_member is None:
        raise HTTPException(status_code=404, detail="会员未找到")
    return db_member


@router.post("/{member_id}/activate", response_model=MemberResponse, summary="激活会员")
@require_permission("member:update")
@audit_action(action="ACTIVATE_MEMBER", resource_type="MEMBER", resource_id=lambda member_id, **kwargs: str(member_id))
def activate_member_endpoint(member_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    激活指定ID的会员。
    - **member_id**: 会员的唯一标识符
    """
    db_member = member_crud.activate_member(db, member_id=member_id)
    if db_member is None:
        raise HTTPException(status_code=404, detail="会员未找到")
    return db_member


@router.post("/{member_id}/membership", response_model=MemberResponse, summary="更新会员会籍")
@require_permission("member:update")
@audit_action(action="UPDATE_MEMBERSHIP", resource_type="MEMBER", resource_id=lambda member_id, **kwargs: str(member_id), get_new_values=lambda months, **kwargs: {"months_added": months})
def update_membership_endpoint(
    member_id: int, months: int = Query(..., gt=0, description="增加的会籍月数"), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    为指定ID的会员增加会籍时长。
    - **member_id**: 会员的唯一标识符
    - **months**: 要增加的会籍月数 (必须大于0)
    """
    db_member = member_crud.update_membership(db, member_id=member_id, months=months)
    if db_member is None:
        raise HTTPException(status_code=404, detail="会员未找到")
    return db_member


@router.post("/{member_id}/points", response_model=MemberResponse, summary="增加会员积分")
@require_permission("member:update")
@audit_action(action="ADD_POINTS", resource_type="MEMBER", resource_id=lambda member_id, **kwargs: str(member_id), get_new_values=lambda points, **kwargs: {"points_added": points})
def add_points_endpoint(
    member_id: int, points: int = Query(..., gt=0, description="增加的积分数量"), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    为指定ID的会员增加积分。
    - **member_id**: 会员的唯一标识符
    - **points**: 要增加的积分数量 (必须大于0)
    """
    db_member = member_crud.add_points(db, member_id=member_id, points=points)
    if db_member is None:
        raise HTTPException(status_code=404, detail="会员未找到")
    return db_member
