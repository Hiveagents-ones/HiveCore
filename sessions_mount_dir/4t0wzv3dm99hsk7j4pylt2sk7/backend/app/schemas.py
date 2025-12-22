from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: str
    is_active: int = 1

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[int] = None

class User(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    roles: List['Role'] = []

class PermissionBase(BaseModel):
    name: str
    resource: str
    action: str
    description: Optional[str] = None

class PermissionCreate(PermissionBase):
    pass

class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    description: Optional[str] = None

class Permission(PermissionBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    permission_ids: List[int] = []

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = None

class Role(RoleBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    permissions: List[Permission] = []
    users: List[User] = []

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class MemberBase(BaseModel):
    name: str
    gender: Optional[str] = None
    contact: Optional[str] = None
    card_type: Optional[str] = None
    coach_id: Optional[int] = None

class MemberCreate(MemberBase):
    pass

class MemberUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    contact: Optional[str] = None
    card_type: Optional[str] = None
    coach_id: Optional[int] = None

class Member(MemberBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    coach: Optional[User] = None

class CourseBase(BaseModel):
    name: str
    coach_id: Optional[int] = None
    time: Optional[datetime] = None
    location: Optional[str] = None

class CourseCreate(CourseBase):
    pass

class CourseUpdate(BaseModel):
    name: Optional[str] = None
    coach_id: Optional[int] = None
    time: Optional[datetime] = None
    location: Optional[str] = None

class Course(CourseBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    coach: Optional[User] = None

class PaymentBase(BaseModel):
    member_id: int
    type: Optional[str] = None
    amount: int

class PaymentCreate(PaymentBase):
    pass

class Payment(PaymentBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    timestamp: datetime
    member: Member

class ReportBase(BaseModel):
    type: str
    data: str

class ReportCreate(ReportBase):
    pass

class Report(ReportBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    generated_at: datetime