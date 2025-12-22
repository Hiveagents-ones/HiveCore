from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class CourseBookingStats(BaseModel):
    course_id: int
    course_name: str
    total_bookings: int
    booking_rate: float
    revenue: float
    
class MemberGrowthStats(BaseModel):
    date: datetime
    new_members: int
    total_members: int
    growth_rate: float
    
class PopularCourseRanking(BaseModel):
    rank: int
    course_id: int
    course_name: str
    booking_count: int
    rating: float
    
class RevenueStats(BaseModel):
    date: datetime
    daily_revenue: float
    monthly_revenue: float
    total_revenue: float
    
class AnalyticsOverview(BaseModel):
    total_bookings: int
    total_members: int
    total_revenue: float
    avg_booking_rate: float
    period_start: datetime
    period_end: datetime
    
class DetailedAnalytics(BaseModel):
    overview: AnalyticsOverview
    booking_stats: List[CourseBookingStats]
    member_growth: List[MemberGrowthStats]
    popular_courses: List[PopularCourseRanking]
    revenue_stats: List[RevenueStats]
    
class AnalyticsRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    course_ids: Optional[List[int]] = None
    include_revenue: bool = True
    include_growth: bool = True
    
class AnalyticsResponse(BaseModel):
    success: bool
    data: DetailedAnalytics
    message: Optional[str] = None
    timestamp: datetime
