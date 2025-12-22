from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MemberTrendResponse(BaseModel):
    dates: List[str]
    new_members: List[int]
    total_members: int
    
    class Config:
        orm_mode = True

class CoursePopularityResponse(BaseModel):
    course_names: List[str]
    booking_counts: List[int]
    revenues: List[float]
    
    class Config:
        orm_mode = True

class RevenueStatsResponse(BaseModel):
    dates: List[str]
    revenues: List[float]
    total_revenue: float
    payment_types: List[str]
    type_revenues: List[float]
    
    class Config:
        orm_mode = True

class ReportRequest(BaseModel):
    report_type: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    parameters: Optional[dict] = None

class ReportResponse(BaseModel):
    id: int
    type: str
    data: dict
    generated_at: datetime
    
    class Config:
        orm_mode = True