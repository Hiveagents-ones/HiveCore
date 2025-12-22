from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from ..database import get_db
from ..services.report_service import ReportService
from ..schemas.report_schemas import MemberTrendResponse, CoursePopularityResponse, RevenueStatsResponse

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

@router.get("/member-trend", response_model=MemberTrendResponse)
async def get_member_trend(
    days: int = Query(default=30, ge=1, le=365),
    dimension: str = Query(default="daily", regex="^(daily|weekly|monthly)$"),
    db: Session = Depends(get_db)
):
    """
    获取会员增长趋势数据
    """
    service = ReportService(db)
    return await service.get_member_trend(days, dimension)

@router.get("/course-popularity", response_model=CoursePopularityResponse)
async def get_course_popularity(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    获取课程受欢迎度数据
    """
    service = ReportService(db)
    return await service.get_course_popularity(days)

@router.get("/revenue-stats", response_model=RevenueStatsResponse)
async def get_revenue_stats(
    days: int = Query(default=30, ge=1, le=365),
    dimension: str = Query(default="daily", regex="^(daily|weekly|monthly)$"),
    db: Session = Depends(get_db)
):
    """
    获取收入统计数据
    """
    service = ReportService(db)
    return await service.get_revenue_stats(days, dimension)