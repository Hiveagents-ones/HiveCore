from functools import wraps
from typing import List, Optional, Callable, Any
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models.rbac import User, Role, Permission

class RBAC:
    def __init__(self, db: Session):
        self.db = db

    def get_user_permissions(self, user_id: int) -> List[str]:
        """Get all permissions for a user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return []
        
        permissions = set()
        for role in user.roles:
            for permission in role.permissions:
                permissions.add(f"{permission.resource}:{permission.action}")
        return list(permissions)

    def has_permission(self, user_id: int, resource: str, action: str) -> bool:
        """Check if user has specific permission"""
        user_permissions = self.get_user_permissions(user_id)
        required_permission = f"{resource}:{action}"
        return required_permission in user_permissions

    def has_role(self, user_id: int, role_name: str) -> bool:
        """Check if user has specific role"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        return any(role.name == role_name for role in user.roles)

def get_current_user_id(user_id: int) -> int:
    """Placeholder for actual user authentication"""
    return user_id

def require_permission(resource: str, action: str):
    """Decorator to require specific permission"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            db: Session = kwargs.get('db') or next(get_db())
            user_id = get_current_user_id(kwargs.get('current_user_id'))
            
            rbac = RBAC(db)
            if not rbac.has_permission(user_id, resource, action):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_role(role_name: str):
    """Decorator to require specific role"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            db: Session = kwargs.get('db') or next(get_db())
            user_id = get_current_user_id(kwargs.get('current_user_id'))
            
            rbac = RBAC(db)
            if not rbac.has_role(user_id, role_name):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient role"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_any_permission(permissions: List[tuple]):
    """Decorator to require any of the specified permissions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            db: Session = kwargs.get('db') or next(get_db())
            user_id = get_current_user_id(kwargs.get('current_user_id'))
            
            rbac = RBAC(db)
            has_any = False
            for resource, action in permissions:
                if rbac.has_permission(user_id, resource, action):
                    has_any = True
                    break
            
            if not has_any:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_all_permissions(permissions: List[tuple]):
    """Decorator to require all specified permissions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            db: Session = kwargs.get('db') or next(get_db())
            user_id = get_current_user_id(kwargs.get('current_user_id'))
            
            rbac = RBAC(db)
            for resource, action in permissions:
                if not rbac.has_permission(user_id, resource, action):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Insufficient permissions"
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Permission constants for easier reference
class Permissions:
    USER_CREATE = ('user', 'create')
    USER_READ = ('user', 'read')
    USER_UPDATE = ('user', 'update')
    USER_DELETE = ('user', 'delete')
    
    PRODUCT_CREATE = ('product', 'create')
    PRODUCT_READ = ('product', 'read')
    PRODUCT_UPDATE = ('product', 'update')
    PRODUCT_DELETE = ('product', 'delete')
    
    ORDER_CREATE = ('order', 'create')
    ORDER_READ = ('order', 'read')
    ORDER_UPDATE = ('order', 'update')
    ORDER_DELETE = ('order', 'delete')
    
    ADMIN_PANEL = ('admin', 'panel')
    SYSTEM_CONFIG = ('system', 'config')

# Role constants
class Roles:
    USER = 'user'
    MERCHANT = 'merchant'
    ADMIN = 'admin'

# Helper function to check permissions in code
def check_permission(db: Session, user_id: int, permission: tuple) -> bool:
    """Helper function to check permission outside of decorators"""
    rbac = RBAC(db)
    return rbac.has_permission(user_id, permission[0], permission[1])

def check_role(db: Session, user_id: int, role_name: str) -> bool:
    """Helper function to check role outside of decorators"""
    rbac = RBAC(db)
    return rbac.has_role(user_id, role_name)
