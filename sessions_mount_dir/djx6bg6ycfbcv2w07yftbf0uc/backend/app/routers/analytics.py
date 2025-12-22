from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..dependencies import get_db, get_redis, get_current_merchant
from ..schemas.analytics import (
    AnalyticsRequest,
    AnalyticsResponse,
    DetailedAnalytics,
    AnalyticsOverview,
    CourseBookingStats,
    MemberGrowthStats,
    PopularCourseRanking,
    RevenueStats
)
from ..services.analytics_service import AnalyticsService
from ..models import Merchant

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=AnalyticsResponse)
async def get_analytics(
    request: AnalyticsRequest,
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    """
    Get comprehensive analytics data for the merchant's store
    """
    try:
        # Validate date range
        if request.end_date < request.start_date:
            raise HTTPException(status_code=400, detail="End date must be after start date")
        
        # Limit date range to 1 year
        if request.end_date - request.start_date > timedelta(days=365):
            raise HTTPException(status_code=400, detail="Date range cannot exceed 1 year")

        service = AnalyticsService(db, redis_client)
        
        # Get overview statistics
        overview = await _get_overview(
            service, 
            current_merchant.id, 
            request.start_date, 
            request.end_date
        )
        
        # Get detailed statistics
        booking_stats = await _get_booking_stats(
            service,
            current_merchant.id,
            request.start_date,
            request.end_date,
            request.course_ids
        )
        
        member_growth = []
        if request.include_growth:
            member_growth = await _get_member_growth(
                service,
                current_merchant.id,
                request.start_date,
                request.end_date
            )
        
        popular_courses = await _get_popular_courses(
            service,
            current_merchant.id,
            request.start_date,
            request.end_date
        )
        
        revenue_stats = []
        if request.include_revenue:
            revenue_stats = await _get_revenue_stats(
                service,
                current_merchant.id,
                request.start_date,
                request.end_date
            )
        
        detailed_analytics = DetailedAnalytics(
            overview=overview,
            booking_stats=booking_stats,
            member_growth=member_growth,
            popular_courses=popular_courses,
            revenue_stats=revenue_stats
        )
        
        return AnalyticsResponse(
            success=True,
            data=detailed_analytics,
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _get_overview(
    service: AnalyticsService,
    merchant_id: int,
    start_date: datetime,
    end_date: datetime
) -> AnalyticsOverview:
    """Get overview statistics"""
    cache_key = service._get_cache_key(
        merchant_id,
        "overview",
        f"{start_date.date()}_{end_date.date()}"
    )
    cached = service._get_cached_data(cache_key)
    if cached:
        return AnalyticsOverview(**cached)
    
    # Calculate total bookings
    total_bookings = service.db.query(Booking).join(Course).filter(
        Course.merchant_id == merchant_id,
        Booking.created_at >= start_date,
        Booking.created_at <= end_date
    ).count()
    
    # Calculate total members
    total_members = service.db.query(Member).filter(
        Member.merchant_id == merchant_id,
        Member.created_at <= end_date
    ).count()
    
    # Calculate total revenue
    total_revenue = service.db.query(func.sum(Payment.amount)).join(Booking).join(Course).filter(
        Course.merchant_id == merchant_id,
        Payment.created_at >= start_date,
        Payment.created_at <= end_date,
        Payment.status == "completed"
    ).scalar() or 0.0
    
    # Calculate average booking rate
    total_slots = service.db.query(func.sum(Course.capacity)).filter(
        Course.merchant_id == merchant_id
    ).scalar() or 0
    avg_booking_rate = (total_bookings / total_slots * 100) if total_slots > 0 else 0.0
    
    overview_data = {
        "total_bookings": total_bookings,
        "total_members": total_members,
        "total_revenue": float(total_revenue),
        "avg_booking_rate": round(avg_booking_rate, 2),
        "period_start": start_date,
        "period_end": end_date
    }
    
    service._set_cache_data(cache_key, overview_data)
    return AnalyticsOverview(**overview_data)


async def _get_booking_stats(
    service: AnalyticsService,
    merchant_id: int,
    start_date: datetime,
    end_date: datetime,
    course_ids: Optional[List[int]]
) -> List[CourseBookingStats]:
    """Get booking statistics by course"""
    cache_key = service._get_cache_key(
        merchant_id,
        "booking_stats",
        f"{start_date.date()}_{end_date.date()}_{course_ids or 'all'}"
    )
    cached = service._get_cached_data(cache_key)
    if cached:
        return [CourseBookingStats(**item) for item in cached]
    
    query = service.db.query(
        Course.id.label('course_id'),
        Course.name.label('course_name'),
        func.count(Booking.id).label('total_bookings'),
        func.sum(Course.capacity).label('total_capacity')
    ).join(Booking).filter(
        Course.merchant_id == merchant_id,
        Booking.created_at >= start_date,
        Booking.created_at <= end_date
    )
    
    if course_ids:
        query = query.filter(Course.id.in_(course_ids))
    
    results = query.group_by(Course.id, Course.name).all()
    
    stats = []
    for r in results:
        booking_rate = (r.total_bookings / r.total_capacity * 100) if r.total_capacity > 0 else 0.0
        revenue = service.db.query(func.sum(Payment.amount)).join(Booking).filter(
            Booking.course_id == r.course_id,
            Payment.created_at >= start_date,
            Payment.created_at <= end_date,
            Payment.status == "completed"
        ).scalar() or 0.0
        
        stats.append(CourseBookingStats(
            course_id=r.course_id,
            course_name=r.course_name,
            total_bookings=r.total_bookings,
            booking_rate=round(booking_rate, 2),
            revenue=float(revenue)
        ))
    
    cache_data = [stat.dict() for stat in stats]
    service._set_cache_data(cache_key, cache_data)
    return stats


async def _get_member_growth(
    service: AnalyticsService,
    merchant_id: int,
    start_date: datetime,
    end_date: datetime
) -> List[MemberGrowthStats]:
    """Get member growth statistics"""
    cache_key = service._get_cache_key(
        merchant_id,
        "member_growth",
        f"{start_date.date()}_{end_date.date()}"
    )
    cached = service._get_cached_data(cache_key)
    if cached:
        return [MemberGrowthStats(**item) for item in cached]
    
    # Get daily member counts
    query = service.db.query(
        func.date(Member.created_at).label('date'),
        func.count(Member.id).label('new_members')
    ).filter(
        Member.merchant_id == merchant_id,
        Member.created_at >= start_date,
        Member.created_at <= end_date
    ).group_by(func.date(Member.created_at))
    
    results = query.all()
    
    # Calculate cumulative totals and growth rates
    stats = []
    total_members = 0
    previous_total = 0
    
    for r in results:
        total_members += r.new_members
        growth_rate = ((total_members - previous_total) / previous_total * 100) if previous_total > 0 else 0.0
        
        stats.append(MemberGrowthStats(
            date=r.date,
            new_members=r.new_members,
            total_members=total_members,
            growth_rate=round(growth_rate, 2)
        ))
        
        previous_total = total_members
    
    cache_data = [stat.dict() for stat in stats]
    service._set_cache_data(cache_key, cache_data)
    return stats


async def _get_popular_courses(
    service: AnalyticsService,
    merchant_id: int,
    start_date: datetime,
    end_date: datetime
) -> List[PopularCourseRanking]:
    """Get popular course rankings"""
    cache_key = service._get_cache_key(
        merchant_id,
        "popular_courses",
        f"{start_date.date()}_{end_date.date()}"
    )
    cached = service._get_cached_data(cache_key)
    if cached:
        return [PopularCourseRanking(**item) for item in cached]
    
    query = service.db.query(
        Course.id.label('course_id'),
        Course.name.label('course_name'),
        func.count(Booking.id).label('booking_count'),
        func.avg(Booking.rating).label('rating')
    ).join(Booking).filter(
        Course.merchant_id == merchant_id,
        Booking.created_at >= start_date,
        Booking.created_at <= end_date
    ).group_by(Course.id, Course.name).order_by(desc(func.count(Booking.id))).limit(10)
    
    results = query.all()
    
    rankings = []
    for idx, r in enumerate(results, 1):
        rankings.append(PopularCourseRanking(
            rank=idx,
            course_id=r.course_id,
            course_name=r.course_name,
            booking_count=r.booking_count,
            rating=round(float(r.rating or 0), 2)
        ))
    
    cache_data = [ranking.dict() for ranking in rankings]
    service._set_cache_data(cache_key, cache_data)
    return rankings


async def _get_revenue_stats(
    service: AnalyticsService,
    merchant_id: int,
    start_date: datetime,
    end_date: datetime
) -> List[RevenueStats]:
    """Get revenue statistics"""
    cache_key = service._get_cache_key(
        merchant_id,
        "revenue_stats",
        f"{start_date.date()}_{end_date.date()}"
    )
    cached = service._get_cached_data(cache_key)
    if cached:
        return [RevenueStats(**item) for item in cached]
    
    # Get daily revenue
    query = service.db.query(
        func.date(Payment.created_at).label('date'),
        func.sum(Payment.amount).label('daily_revenue')
    ).join(Booking).join(Course).filter(
        Course.merchant_id == merchant_id,
        Payment.created_at >= start_date,
        Payment.created_at <= end_date,
        Payment.status == "completed"
    ).group_by(func.date(Payment.created_at))
    
    results = query.all()
    
    stats = []
    total_revenue = 0.0
    monthly_revenue = 0.0
    current_month = None
    
    for r in results:
        total_revenue += float(r.daily_revenue)
        
        # Reset monthly revenue at month change
        if current_month != r.date.month:
            monthly_revenue = 0.0
            current_month = r.date.month
        
        monthly_revenue += float(r.daily_revenue)
        
        stats.append(RevenueStats(
            date=r.date,
            daily_revenue=float(r.daily_revenue),
            monthly_revenue=monthly_revenue,
            total_revenue=total_revenue
        ))
    
    cache_data = [stat.dict() for stat in stats]
    service._set_cache_data(cache_key, cache_data)
    return stats