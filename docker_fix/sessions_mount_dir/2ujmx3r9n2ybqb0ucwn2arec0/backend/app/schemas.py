from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class CoachBase(BaseModel):
    name: str = Field(..., example="John Doe")
    email: str = Field(..., example="john.doe@example.com")
    phone: Optional[str] = Field(None, example="+1234567890")
    specialization: Optional[str] = Field(None, example="Yoga")
    bio: Optional[str] = Field(None, example="Experienced yoga instructor with 10 years of practice.")
    is_active: bool = Field(True, example=True)


class CoachCreate(CoachBase):
    pass


class CoachUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    specialization: Optional[str] = None
    bio: Optional[str] = None
    is_active: Optional[bool] = None


class Coach(CoachBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CourseBase(BaseModel):
    name: str = Field(..., example="Morning Yoga")
    description: Optional[str] = Field(None, example="A relaxing start to your day with gentle yoga stretches.")
    max_capacity: int = Field(..., example=20)
    remaining_slots: int = Field(..., example=15)
    start_time: datetime = Field(..., example="2023-10-27T09:00:00Z")
    end_time: datetime = Field(..., example="2023-10-27T10:00:00Z")
    coach_id: int = Field(..., example=1)


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    max_capacity: Optional[int] = None
    remaining_slots: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    coach_id: Optional[int] = None


class Course(CourseBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    coach: Coach

    class Config:
        from_attributes = True


class BookingBase(BaseModel):
    member_name: str = Field(..., example="Jane Smith")
    member_email: str = Field(..., example="jane.smith@example.com")
    member_phone: Optional[str] = Field(None, example="+1234567890")
    status: str = Field("confirmed", example="confirmed")
    course_id: int = Field(..., example=1)


class BookingCreate(BookingBase):
    pass


class BookingUpdate(BaseModel):
    member_name: Optional[str] = None
    member_email: Optional[str] = None
    member_phone: Optional[str] = None
    status: Optional[str] = None
    course_id: Optional[int] = None


class Booking(BookingBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    course: Course

    class Config:
        from_attributes = True


class CourseList(BaseModel):
    id: int
    name: str
    start_time: datetime
    end_time: datetime
    remaining_slots: int
    coach: Coach

    class Config:
        from_attributes = True


class CoachList(BaseModel):
    id: int
    name: str
    specialization: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True
