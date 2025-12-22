from enum import Enum
from typing import List, Dict, Optional, Set
from functools import wraps
from fastapi import HTTPException, status
from ..models.member import Member

class Permission(Enum):
    """系统权限枚举"""
    # 会员管理权限
    MEMBER_CREATE = "member:create"
    MEMBER_READ = "member:read"
    MEMBER_UPDATE = "member:update"
    MEMBER_DELETE = "member:delete"
    
    # 会员等级管理权限
    MEMBER_PLAN_READ = "member_plan:read"
    MEMBER_PLAN_UPDATE = "member_plan:update"
    
    # 系统管理权限
    SYSTEM_ADMIN = "system:admin"

class Role(Enum):
    """系统角色枚举"""
    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"
    MEMBER = "member"

# 角色权限映射
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        Permission.MEMBER_CREATE,
        Permission.MEMBER_READ,
        Permission.MEMBER_UPDATE,
        Permission.MEMBER_DELETE,
        Permission.MEMBER_PLAN_READ,
        Permission.MEMBER_PLAN_UPDATE,
        Permission.SYSTEM_ADMIN,
    },
    Role.MANAGER: {
        Permission.MEMBER_CREATE,
        Permission.MEMBER_READ,
        Permission.MEMBER_UPDATE,
        Permission.MEMBER_PLAN_READ,
        Permission.MEMBER_PLAN_UPDATE,
    },
    Role.STAFF: {
        Permission.MEMBER_READ,
        Permission.MEMBER_UPDATE,
    },
    Role.MEMBER: {
        Permission.MEMBER_READ,
    },
}

class RBAC:
    """基于角色的访问控制"""
    
    @staticmethod
    def has_permission(user_role: Role, permission: Permission) -> bool:
        """检查用户角色是否具有指定权限"""
        return permission in ROLE_PERMISSIONS.get(user_role, set())
    
    @staticmethod
    def has_any_permission(user_role: Role, permissions: List[Permission]) -> bool:
        """检查用户角色是否具有任一权限"""
        user_permissions = ROLE_PERMISSIONS.get(user_role, set())
        return any(perm in user_permissions for perm in permissions)
    
    @staticmethod
    def has_all_permissions(user_role: Role, permissions: List[Permission]) -> bool:
        """检查用户角色是否具有所有权限"""
        user_permissions = ROLE_PERMISSIONS.get(user_role, set())
        return all(perm in user_permissions for perm in permissions)
    
    @staticmethod
    def get_role_permissions(role: Role) -> Set[Permission]:
        """获取角色的所有权限"""
        return ROLE_PERMISSIONS.get(role, set())

def require_permission(permission: Permission):
    """权限检查装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从kwargs中获取当前用户角色
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未认证用户"
                )
            
            user_role = Role(current_user.role)
            if not RBAC.has_permission(user_role, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"权限不足，需要权限: {permission.value}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_any_permission(permissions: List[Permission]):
    """需要任一权限的装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未认证用户"
                )
            
            user_role = Role(current_user.role)
            if not RBAC.has_any_permission(user_role, permissions):
                perm_values = [p.value for p in permissions]
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"权限不足，需要以下任一权限: {', '.join(perm_values)}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def check_member_ownership(current_user, member_id: int) -> bool:
    """检查用户是否是会员本人或具有管理权限"""
    if Role(current_user.role) in [Role.ADMIN, Role.MANAGER, Role.STAFF]:
        return True
    
    # 检查是否是会员本人
    if hasattr(current_user, 'member_id') and current_user.member_id == member_id:
        return True
    
    return False

def require_member_ownership_or_permission(permission: Permission):
    """需要会员所有权或特定权限的装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            member_id = kwargs.get('member_id')
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未认证用户"
                )
            
            if not member_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="缺少会员ID"
                )
            
            user_role = Role(current_user.role)
            
            # 检查权限或所有权
            if not (RBAC.has_permission(user_role, permission) or 
                   check_member_ownership(current_user, member_id)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="权限不足或无权访问该会员信息"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
