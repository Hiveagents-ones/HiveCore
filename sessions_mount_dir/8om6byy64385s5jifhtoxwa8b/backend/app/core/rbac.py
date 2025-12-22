from enum import Enum
from typing import List, Optional, Set
from fastapi import HTTPException, status
from app.core.security import get_current_user


class Permission(Enum):
    """系统权限枚举"""
    # 会员管理权限
    MEMBER_CREATE = "member:create"
    MEMBER_READ = "member:read"
    MEMBER_UPDATE = "member:update"
    MEMBER_DELETE = "member:delete"
    
    # 系统管理权限
    USER_MANAGE = "user:manage"
    ROLE_MANAGE = "role:manage"
    SYSTEM_CONFIG = "system:config"


class Role(Enum):
    """系统角色枚举"""
    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"
    MEMBER = "member"

    @property
    def permissions(self) -> Set[Permission]:
        """获取角色对应的权限集合"""
        role_permissions = {
            Role.ADMIN: {
                Permission.MEMBER_CREATE,
                Permission.MEMBER_READ,
                Permission.MEMBER_UPDATE,
                Permission.MEMBER_DELETE,
                Permission.USER_MANAGE,
                Permission.ROLE_MANAGE,
                Permission.SYSTEM_CONFIG,
            },
            Role.MANAGER: {
                Permission.MEMBER_CREATE,
                Permission.MEMBER_READ,
                Permission.MEMBER_UPDATE,
                Permission.MEMBER_DELETE,
            },
            Role.STAFF: {
                Permission.MEMBER_READ,
                Permission.MEMBER_UPDATE,
            },
            Role.MEMBER: {
                Permission.MEMBER_READ,
            },
        }
        return role_permissions.get(self, set())


class RBAC:
    """基于角色的访问控制类"""
    
    @staticmethod
    def has_permission(user_role: Role, permission: Permission) -> bool:
        """检查用户角色是否具有指定权限"""
        return permission in user_role.permissions
    
    @staticmethod
    def has_any_permission(user_role: Role, permissions: List[Permission]) -> bool:
        """检查用户角色是否具有任一指定权限"""
        return any(perm in user_role.permissions for perm in permissions)
    
    @staticmethod
    def has_all_permissions(user_role: Role, permissions: List[Permission]) -> bool:
        """检查用户角色是否具有所有指定权限"""
        return all(perm in user_role.permissions for perm in permissions)
    
    @staticmethod
    def check_permission(user_role: Role, permission: Permission):
        """检查权限，如果没有权限则抛出异常"""
        if not RBAC.has_permission(user_role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
    
    @staticmethod
    def get_user_permissions(user_role: Role) -> List[str]:
        """获取用户角色的所有权限列表"""
        return [perm.value for perm in user_role.permissions]


def require_permission(permission: Permission):
    """装饰器：要求用户具有指定权限"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            current_user = await get_current_user()
            user_role = Role(current_user.role)
            RBAC.check_permission(user_role, permission)
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(permissions: List[Permission]):
    """装饰器：要求用户具有任一指定权限"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            current_user = await get_current_user()
            user_role = Role(current_user.role)
            if not RBAC.has_any_permission(user_role, permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_all_permissions(permissions: List[Permission]):
    """装饰器：要求用户具有所有指定权限"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            current_user = await get_current_user()
            user_role = Role(current_user.role)
            if not RBAC.has_all_permissions(user_role, permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
