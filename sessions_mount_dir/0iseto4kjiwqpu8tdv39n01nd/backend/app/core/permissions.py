from enum import Enum
from typing import List, Optional, Set
from fastapi import HTTPException, status


class Permission(Enum):
    """系统权限枚举"""
    # 基础权限
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    
    # 会籍管理权限
    VIEW_MEMBERSHIP = "view_membership"
    MANAGE_MEMBERSHIP = "manage_membership"
    PROCESS_PAYMENT = "process_payment"
    VIEW_TRANSACTIONS = "view_transactions"
    
    # 系统管理权限
    # 教练管理权限
    VIEW_COACHES = "view_coaches"
    MANAGE_COACHES = "manage_coaches"
    ASSIGN_COACHES = "assign_coaches"
    ADMIN = "admin"
    MANAGE_USERS = "manage_users"
    VIEW_REPORTS = "view_reports"


class Role(Enum):
    """系统角色枚举"""
    GUEST = "guest"
    MEMBER = "member"
    PREMIUM_MEMBER = "premium_member"
    STAFF = "staff"
    ADMIN = "admin"


# 角色权限映射
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.GUEST: {
        Permission.READ,
    },
    Role.MEMBER: {
        Permission.READ,
        Permission.WRITE,
        Permission.VIEW_MEMBERSHIP,
        Permission.VIEW_TRANSACTIONS,
    },
    Role.PREMIUM_MEMBER: {
        Permission.READ,
        Permission.WRITE,
        Permission.VIEW_MEMBERSHIP,
        Permission.MANAGE_MEMBERSHIP,
        Permission.VIEW_TRANSACTIONS,
    },
    Role.STAFF: {
        Permission.READ,
        Permission.WRITE,
        Permission.VIEW_MEMBERSHIP,
        Permission.MANAGE_MEMBERSHIP,
        Permission.PROCESS_PAYMENT,
        Permission.VIEW_TRANSACTIONS,
        Permission.VIEW_REPORTS,
        Permission.VIEW_COACHES,
    },
    Role.ADMIN: {
        Permission.READ,
        Permission.WRITE,
        Permission.DELETE,
        Permission.VIEW_MEMBERSHIP,
        Permission.MANAGE_MEMBERSHIP,
        Permission.PROCESS_PAYMENT,
        Permission.VIEW_TRANSACTIONS,
        Permission.ADMIN,
        Permission.MANAGE_USERS,
        Permission.VIEW_REPORTS,
        Permission.VIEW_COACHES,
        Permission.MANAGE_COACHES,
        Permission.ASSIGN_COACHES,
    },
}


class PermissionChecker:
    """权限检查器"""
    
    def __init__(self, user_role: Role):
        self.user_role = user_role
        self.user_permissions = ROLE_PERMISSIONS.get(user_role, set())
    
    def has_permission(self, permission: Permission) -> bool:
        """检查用户是否具有指定权限"""
        return permission in self.user_permissions
    
    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """检查用户是否具有任意一个指定权限"""
        return any(perm in self.user_permissions for perm in permissions)
    
    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        """检查用户是否具有所有指定权限"""
        return all(perm in self.user_permissions for perm in permissions)
    
    def require_permission(self, permission: Permission):
        """要求用户具有指定权限，否则抛出异常"""
        if not self.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission.value}' required"
            )
    
    def require_any_permission(self, permissions: List[Permission]):
        """要求用户具有任意一个指定权限，否则抛出异常"""
        if not self.has_any_permission(permissions):
            perms_str = ", ".join(p.value for p in permissions)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of the following permissions required: {perms_str}"
            )
    
    def require_all_permissions(self, permissions: List[Permission]):
        """要求用户具有所有指定权限，否则抛出异常"""
        if not self.has_all_permissions(permissions):
            perms_str = ", ".join(p.value for p in permissions)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"All of the following permissions required: {perms_str}"
            )


def get_permission_checker(user_role: Role) -> PermissionChecker:
    """获取权限检查器实例"""
    return PermissionChecker(user_role)


def check_permission(user_role: Role, permission: Permission) -> bool:
    """快速检查权限"""
    checker = get_permission_checker(user_role)
    return checker.has_permission(permission)


def require_permission(user_role: Role, permission: Permission):
    """快速要求权限"""
    checker = get_permission_checker(user_role)
    checker.require_permission(permission)


# 会籍相关权限检查函数
def can_view_membership(user_role: Role) -> bool:
    """检查是否可以查看会籍信息"""
    return check_permission(user_role, Permission.VIEW_MEMBERSHIP)


def can_manage_membership(user_role: Role) -> bool:
    """检查是否可以管理会籍"""
    return check_permission(user_role, Permission.MANAGE_MEMBERSHIP)


def can_process_payment(user_role: Role) -> bool:
    """检查是否可以处理支付"""
    return check_permission(user_role, Permission.PROCESS_PAYMENT)


def can_view_transactions(user_role: Role) -> bool:
    """检查是否可以查看交易记录"""
    return check_permission(user_role, Permission.VIEW_TRANSACTIONS)


def require_manage_membership(user_role: Role):
    """要求会籍管理权限"""
    require_permission(user_role, Permission.MANAGE_MEMBERSHIP)


def require_process_payment(user_role: Role):
    """要求支付处理权限"""
    require_permission(user_role, Permission.PROCESS_PAYMENT)


# 教练相关权限检查函数
def can_view_coaches(user_role: Role) -> bool:
    """检查是否可以查看教练信息"""
    return check_permission(user_role, Permission.VIEW_COACHES)


def can_manage_coaches(user_role: Role) -> bool:
    """检查是否可以管理教练"""
    return check_permission(user_role, Permission.MANAGE_COACHES)


def can_assign_coaches(user_role: Role) -> bool:
    """检查是否可以分配教练"""
    return check_permission(user_role, Permission.ASSIGN_COACHES)


def require_manage_coaches(user_role: Role):
    """要求教练管理权限"""
    require_permission(user_role, Permission.MANAGE_COACHES)


def require_assign_coaches(user_role: Role):
    """要求教练分配权限"""
    require_permission(user_role, Permission.ASSIGN_COACHES)