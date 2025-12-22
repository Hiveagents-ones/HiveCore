from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.member import MemberStatus

class MemberBase(BaseModel):
    name: str
    contact: str
    card_number: str
    level: str
    status: MemberStatus = MemberStatus.ACTIVE

class MemberCreate(MemberBase):
    pass

class MemberUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    card_number: Optional[str] = None
    level: Optional[str] = None
    status: Optional[MemberStatus] = None

class MemberInDB(MemberBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Member(MemberInDB):
    pass

class MemberResponse(BaseModel):
    id: int
    name: str
    contact: str
    card_number: str
    level: str
    status: MemberStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
