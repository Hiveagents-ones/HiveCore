from typing import Optional, List
from pydantic import BaseModel, EmailStr
from datetime import datetime


class CoachBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    specialties: Optional[str] = None
    experience_years: Optional[int] = None
    is_active: bool = True


class CoachCreate(CoachBase):
    pass


class CoachUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    specialties: Optional[str] = None
    experience_years: Optional[int] = None
    is_active: Optional[bool] = None


class CoachInDB(CoachBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class Coach(CoachInDB):
    pass


class CoachList(BaseModel):
    coaches: List[Coach]
    total: int
    page: int
    per_page: int
