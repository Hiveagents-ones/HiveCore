from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.core.security import get_current_admin_user
from app.services.user_service import UserService

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("/", response_model=List[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    is_banned: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    获取所有用户列表（管理员权限）
    """
    user_service = UserService(db)
    users = user_service.get_users(
        skip=skip,
        limit=limit,
        search=search,
        is_banned=is_banned
    )
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    获取特定用户详情（管理员权限）
    """
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.put("/{user_id}/ban", response_model=UserResponse)
async def ban_user(
    user_id: int,
    ban_reason: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    封禁用户（管理员权限）
    """
    user_service = UserService(db)
    user = user_service.ban_user(user_id, ban_reason, current_admin.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.put("/{user_id}/unban", response_model=UserResponse)
async def unban_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    解封用户（管理员权限）
    """
    user_service = UserService(db)
    user = user_service.unban_user(user_id, current_admin.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    更新用户信息（管理员权限）
    """
    user_service = UserService(db)
    user = user_service.update_user(user_id, user_update)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.get("/{user_id}/appeals")
async def get_user_appeals(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    获取用户申诉列表（管理员权限）
    """
    user_service = UserService(db)
    appeals = user_service.get_user_appeals(user_id)
    return appeals


@router.post("/{user_id}/appeals/{appeal_id}/resolve")
async def resolve_appeal(
    user_id: int,
    appeal_id: int,
    resolution: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    处理用户申诉（管理员权限）
    """
    user_service = UserService(db)
    result = user_service.resolve_appeal(
        appeal_id=appeal_id,
        resolution=resolution,
        admin_id=current_admin.id
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appeal not found"
        )
    return {"message": "Appeal resolved successfully"}
