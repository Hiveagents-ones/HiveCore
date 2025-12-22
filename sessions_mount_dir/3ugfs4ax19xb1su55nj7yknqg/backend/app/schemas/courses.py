from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CourseBase(BaseModel):
    name: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    coach_id: int
    max_capacity: int
    current_enrollment: int = 0


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    coach_id: Optional[int] = None
    max_capacity: Optional[int] = None
    current_enrollment: Optional[int] = None


class Course(CourseBase):
    id: int

    class Config:
        orm_mode = True


class CourseBooking(BaseModel):
    member_id: int
    course_id: int