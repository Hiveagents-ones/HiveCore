from pydantic import BaseModel, EmailStr, ConfigDict
from typing import List, Optional
from datetime import datetime

# Base schemas
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# Permission schemas
class PermissionBase(BaseSchema):
    name: str
    resource: str
    action: str
    description: Optional[str] = None

class PermissionCreate(PermissionBase):
    pass

class PermissionUpdate(BaseSchema):
    name: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    description: Optional[str] = None

class Permission(PermissionBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

# Role schemas
class RoleBase(BaseSchema):
    name: str
    description: Optional[str] = None
    is_active: bool = True

class RoleCreate(RoleBase):
    permission_ids: Optional[List[int]] = None

class RoleUpdate(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    permission_ids: Optional[List[int]] = None

class Role(RoleBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    permissions: List[Permission] = []

# User schemas
class UserBase(BaseSchema):
    username: str
    email: EmailStr
    is_active: bool = True

class UserCreate(UserBase):
    password: str
    role_ids: Optional[List[int]] = None

class UserUpdate(BaseSchema):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None
    role_ids: Optional[List[int]] = None

class User(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    roles: List[Role] = []

# Response schemas with nested relationships
class UserWithRoles(User):
    roles: List[Role] = []

class RoleWithPermissions(Role):
    permissions: List[Permission] = []

# Permission check response
class PermissionCheckResponse(BaseSchema):
    has_permission: bool
    resource: str
    action: str

# Role assignment
class RoleAssignment(BaseSchema):
    user_id: int
    role_ids: List[int]

# Permission assignment
class PermissionAssignment(BaseSchema):
    role_id: int
    permission_ids: List[int]
