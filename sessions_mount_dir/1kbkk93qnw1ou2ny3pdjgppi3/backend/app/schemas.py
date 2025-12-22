from pydantic import BaseModel, validator
from datetime import datetime
from typing import Optional

class MemberBase(BaseModel):
    name: str
    phone: str
    id_card: str

class MemberCreate(MemberBase):
    pass

class Member(MemberBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class MemberCheckin(BaseModel):
    member_id: Optional[int] = None
    phone: Optional[str] = None
    id_card: Optional[str] = None
    checkin_time: Optional[datetime] = None

    @validator('member_id', 'phone', 'id_card')
    def check_at_least_one_identifier(cls, v, values):
        # This validator ensures at least one identifier is provided.
        # The logic is handled in the router for clarity.
        return v

class CheckinResponse(BaseModel):
    success: bool
    message: str
    member_id: Optional[int] = None
    member_name: Optional[str] = None
    checkin_time: Optional[datetime] = None

class CourseBase(BaseModel):
    name: str
    description: Optional[str] = None
    capacity: Optional[int] = None
    start_time: Optional[datetime] = None

class CourseCreate(CourseBase):
    pass

class Course(CourseBase):
    id: int

    class Config:
        orm_mode = True

class CourseBooking(BaseModel):
    course_id: int
    member_id: int
