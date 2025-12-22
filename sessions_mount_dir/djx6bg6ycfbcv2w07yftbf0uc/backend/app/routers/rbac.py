from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..services.rbac_service import RBACService
from ..schemas.rbac import (
    User, UserCreate, UserUpdate, UserWithRoles,
    Role, RoleCreate, RoleUpdate, RoleWithPermissions,
    Permission, PermissionCreate, PermissionUpdate,
    PermissionCheckResponse, RoleAssignment, PermissionAssignment
)
from ..core.database import get_db

router = APIRouter(prefix="/rbac", tags=["RBAC"])

# Helper function to get RBAC service
def get_rbac_service(db: Session = Depends(get_db)):
    return RBACService(db)

# User endpoints
@router.post("/users/", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, rbac_service: RBACService = Depends(get_rbac_service)):
    """Create a new user"""
    try:
        return rbac_service.create_user(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/users/{user_id}", response_model=UserWithRoles)
def get_user(user_id: int, rbac_service: RBACService = Depends(get_rbac_service)):
    """Get user by ID"""
    user = rbac_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.put("/users/{user_id}", response_model=User)
def update_user(user_id: int, user_update: UserUpdate, rbac_service: RBACService = Depends(get_rbac_service)):
    """Update user"""
    user = rbac_service.update_user(user_id, user_update)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, rbac_service: RBACService = Depends(get_rbac_service)):
    """Delete user"""
    success = rbac_service.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

@router.post("/users/{user_id}/roles", response_model=UserWithRoles)
def assign_roles_to_user(user_id: int, role_assignment: RoleAssignment, rbac_service: RBACService = Depends(get_rbac_service)):
    """Assign roles to a user"""
    if role_assignment.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User ID mismatch")
    
    user = rbac_service.assign_roles_to_user(user_id, role_assignment.role_ids)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

# Role endpoints
@router.post("/roles/", response_model=Role, status_code=status.HTTP_201_CREATED)
def create_role(role: RoleCreate, rbac_service: RBACService = Depends(get_rbac_service)):
    """Create a new role"""
    try:
        return rbac_service.create_role(role)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/roles/{role_id}", response_model=RoleWithPermissions)
def get_role(role_id: int, rbac_service: RBACService = Depends(get_rbac_service)):
    """Get role by ID"""
    role = rbac_service.get_role(role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role

@router.put("/roles/{role_id}", response_model=Role)
def update_role(role_id: int, role_update: RoleUpdate, rbac_service: RBACService = Depends(get_rbac_service)):
    """Update role"""
    role = rbac_service.update_role(role_id, role_update)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role

@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(role_id: int, rbac_service: RBACService = Depends(get_rbac_service)):
    """Delete role"""
    success = rbac_service.delete_role(role_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

@router.post("/roles/{role_id}/permissions", response_model=RoleWithPermissions)
def assign_permissions_to_role(role_id: int, permission_assignment: PermissionAssignment, rbac_service: RBACService = Depends(get_rbac_service)):
    """Assign permissions to a role"""
    if permission_assignment.role_id != role_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role ID mismatch")
    
    role = rbac_service.assign_permissions_to_role(role_id, permission_assignment.permission_ids)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role

# Permission endpoints
@router.post("/permissions/", response_model=Permission, status_code=status.HTTP_201_CREATED)
def create_permission(permission: PermissionCreate, rbac_service: RBACService = Depends(get_rbac_service)):
    """Create a new permission"""
    try:
        return rbac_service.create_permission(permission)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/permissions/{permission_id}", response_model=Permission)
def get_permission(permission_id: int, rbac_service: RBACService = Depends(get_rbac_service)):
    """Get permission by ID"""
    permission = rbac_service.get_permission(permission_id)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return permission

@router.put("/permissions/{permission_id}", response_model=Permission)
def update_permission(permission_id: int, permission_update: PermissionUpdate, rbac_service: RBACService = Depends(get_rbac_service)):
    """Update permission"""
    permission = rbac_service.update_permission(permission_id, permission_update)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return permission

@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_permission(permission_id: int, rbac_service: RBACService = Depends(get_rbac_service)):
    """Delete permission"""
    success = rbac_service.delete_permission(permission_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

# Permission check endpoint
@router.get("/users/{user_id}/permissions/check", response_model=PermissionCheckResponse)
def check_user_permission(user_id: int, resource: str, action: str, rbac_service: RBACService = Depends(get_rbac_service)):
    """Check if a user has a specific permission"""
    has_permission = rbac_service.check_user_permission(user_id, resource, action)
    return PermissionCheckResponse(
        has_permission=has_permission,
        resource=resource,
        action=action
    )
