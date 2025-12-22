from functools import wraps
from typing import List, Optional, Callable, Any
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.permission import User, Role, Permission

def check_permission(user: User, required_permission: str) -> bool:
    """
    Check if a user has a specific permission.
    
    Args:
        user: The user object
        required_permission: The permission code to check (e.g., 'member:create')
    
    Returns:
        bool: True if user has permission, False otherwise
    """
    if user.is_superuser:
        return True
    
    # Get all permissions for the user through their roles
    user_permissions = set()
    for role in user.roles:
        if role.is_active:
            for permission in role.permissions:
                if permission.is_active:
                    user_permissions.add(permission.code)
    
    return required_permission in user_permissions

def require_permission(permission: str):
    """
    Decorator to require specific permission for an endpoint.
    
    Args:
        permission: The permission code required (e.g., 'member:create')
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs (should be injected by auth middleware)
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not check_permission(current_user, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission}' required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_any_permission(permissions: List[str]):
    """
    Decorator to require any of the specified permissions for an endpoint.
    
    Args:
        permissions: List of permission codes (user needs at least one)
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if current_user.is_superuser:
                return await func(*args, **kwargs)
            
            # Get all permissions for the user
            user_permissions = set()
            for role in current_user.roles:
                if role.is_active:
                    for permission in role.permissions:
                        if permission.is_active:
                            user_permissions.add(permission.code)
            
            # Check if user has any of the required permissions
            if not any(perm in user_permissions for perm in permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"One of the following permissions required: {', '.join(permissions)}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_all_permissions(permissions: List[str]):
    """
    Decorator to require all specified permissions for an endpoint.
    
    Args:
        permissions: List of permission codes (user needs all of them)
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if current_user.is_superuser:
                return await func(*args, **kwargs)
            
            # Get all permissions for the user
            user_permissions = set()
            for role in current_user.roles:
                if role.is_active:
                    for permission in role.permissions:
                        if permission.is_active:
                            user_permissions.add(permission.code)
            
            # Check if user has all required permissions
            missing_permissions = [perm for perm in permissions if perm not in user_permissions]
            if missing_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permissions: {', '.join(missing_permissions)}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def has_permission(user: User, permission: str, db: Session) -> bool:
    """
    Check if a user has a specific permission (database version).
    
    Args:
        user: The user object
        permission: The permission code to check
        db: Database session
    
    Returns:
        bool: True if user has permission, False otherwise
    """
    if user.is_superuser:
        return True
    
    # Query user with all their roles and permissions
    db_user = db.query(User).filter(User.id == user.id).first()
    if not db_user:
        return False
    
    # Collect all permission codes
    user_permissions = set()
    for role in db_user.roles:
        if role.is_active:
            for perm in role.permissions:
                if perm.is_active:
                    user_permissions.add(perm.code)
    
    return permission in user_permissions

def get_user_permissions(user: User, db: Session) -> List[str]:
    """
    Get all permissions for a user.
    
    Args:
        user: The user object
        db: Database session
    
    Returns:
        List of permission codes
    """
    if user.is_superuser:
        # Superuser has all permissions
        all_permissions = db.query(Permission).filter(Permission.is_active == True).all()
        return [perm.code for perm in all_permissions]
    
    # Query user with all their roles and permissions
    db_user = db.query(User).filter(User.id == user.id).first()
    if not db_user:
        return []
    
    # Collect all permission codes
    user_permissions = set()
    for role in db_user.roles:
        if role.is_active:
            for perm in role.permissions:
                if perm.is_active:
                    user_permissions.add(perm.code)
    
    return list(user_permissions)
