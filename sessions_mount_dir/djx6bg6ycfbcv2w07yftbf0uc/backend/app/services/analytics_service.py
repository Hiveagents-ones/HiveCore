from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
import redis
import json
from ..models import Booking, Course, Member, Payment
from ..schemas.analytics import (
    BookingTrendResponse,
    MemberGrowthResponse,
    PopularCourseResponse,
    RevenueStatsResponse
)


class AnalyticsService:
    def __init__(self, db: Session, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client
        self.cache_ttl = 300  # 5 minutes

    def _get_cache_key(self, merchant_id: int, metric: str, params: str = "") -> str:
        """Generate cache key for analytics data"""
        return f"analytics:{merchant_id}:{metric}:{params}"

    def _get_cached_data(self, key: str) -> Optional[Dict]:
        """Get cached data from Redis"""
        try:
            data = self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None

    def _set_cache_data(self, key: str, data: Dict) -> None:
        """Set data to Redis cache"""
        try:
            self.redis.setex(key, self.cache_ttl, json.dumps(data))
        except Exception:
            pass

    def get_booking_trends(
        self,
        merchant_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> BookingTrendResponse:
        """Get booking trends for a merchant within date range"""
        cache_key = self._get_cache_key(
            merchant_id,
            "booking_trends",
            f"{start_date.date()}_{end_date.date()}"
        )
        cached = self._get_cached_data(cache_key)
        if cached:
            return BookingTrendResponse(**cached)

        # Query booking data grouped by date
        query = (
            self.db.query(
                func.date(Booking.created_at).label('date'),
                func.count(Booking.id).label('count')
            )
            .join(Course, Booking.course_id == Course.id)
            .filter(
                and_(
                    Course.merchant_id == merchant_id,
                    Booking.created_at >= start_date,
                    Booking.created_at <= end_date
                )
            )
            .group_by(func.date(Booking.created_at))
            .order_by(func.date(Booking.created_at))
        )

        results = query.all()
        
        # Format response
        dates = [str(r.date) for r in results]
        counts = [r.count for r in results]
        
        response_data = {
            "dates": dates,
            "counts": counts,
            "total_bookings": sum(counts)
        }
        
        self._set_cache_data(cache_key, response_data)
        return BookingTrendResponse(**response_data)

    def get_member_growth(
        self,
        merchant_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> MemberGrowthResponse:
        """Get member growth trends for a merchant"""
        cache_key = self._get_cache_key(
            merchant_id,
            "member_growth",
            f"{start_date.date()}_{end_date.date()}"
        )
        cached = self._get_cached_data(cache_key)
        if cached:
            return MemberGrowthResponse(**cached)

        # Query member registration data
        query = (
            self.db.query(
                func.date(Member.created_at).label('date'),
                func.count(Member.id).label('count')
            )
            .filter(
                and_(
                    Member.merchant_id == merchant_id,
                    Member.created_at >= start_date,
                    Member.created_at <= end_date
                )
            )
            .group_by(func.date(Member.created_at))
            .order_by(func.date(Member.created_at))
        )

        results = query.all()
        
        # Calculate cumulative growth
        dates = [str(r.date) for r in results]
        daily_counts = [r.count for r in results]
        cumulative_counts = []
        total = 0
        for count in daily_counts:
            total += count
            cumulative_counts.append(total)
        
        response_data = {
            "dates": dates,
            "new_members": daily_counts,
            "total_members": cumulative_counts,
            "growth_rate": self._calculate_growth_rate(cumulative_counts)
        }
        
        self._set_cache_data(cache_key, response_data)
        return MemberGrowthResponse(**response_data)

    def get_popular_courses(
        self,
        merchant_id: int,
        limit: int = 10
    ) -> List[PopularCourseResponse]:
        """Get most popular courses for a merchant"""
        cache_key = self._get_cache_key(
            merchant_id,
            "popular_courses",
            f"limit_{limit}"
        )
        cached = self._get_cached_data(cache_key)
        if cached:
            return [PopularCourseResponse(**item) for item in cached]

        # Query course booking counts
        query = (
            self.db.query(
                Course.id,
                Course.name,
                func.count(Booking.id).label('booking_count')
            )
            .join(Booking, Course.id == Booking.course_id)
            .filter(Course.merchant_id == merchant_id)
            .group_by(Course.id, Course.name)
            .order_by(desc(func.count(Booking.id)))
            .limit(limit)
        )

        results = query.all()
        
        response_data = [
            {
                "course_id": r.id,
                "course_name": r.name,
                "booking_count": r.booking_count
            }
            for r in results
        ]
        
        self._set_cache_data(cache_key, response_data)
        return [PopularCourseResponse(**item) for item in response_data]

    def get_revenue_stats(
        self,
        merchant_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> RevenueStatsResponse:
        """Get revenue statistics for a merchant"""
        cache_key = self._get_cache_key(
            merchant_id,
            "revenue_stats",
            f"{start_date.date()}_{end_date.date()}"
        )
        cached = self._get_cached_data(cache_key)
        if cached:
            return RevenueStatsResponse(**cached)

        # Query payment data
        query = (
            self.db.query(
                func.date(Payment.created_at).label('date'),
                func.sum(Payment.amount).label('revenue')
            )
            .join(Booking, Payment.booking_id == Booking.id)
            .join(Course, Booking.course_id == Course.id)
            .filter(
                and_(
                    Course.merchant_id == merchant_id,
                    Payment.status == 'completed',
                    Payment.created_at >= start_date,
                    Payment.created_at <= end_date
                )
            )
            .group_by(func.date(Payment.created_at))
            .order_by(func.date(Payment.created_at))
        )

        results = query.all()
        
        dates = [str(r.date) for r in results]
        revenues = [float(r.revenue or 0) for r in results]
        
        response_data = {
            "dates": dates,
            "revenues": revenues,
            "total_revenue": sum(revenues),
            "average_daily_revenue": sum(revenues) / len(revenues) if revenues else 0
        }
        
        self._set_cache_data(cache_key, response_data)
        return RevenueStatsResponse(**response_data)

    def _calculate_growth_rate(self, cumulative_counts: List[int]) -> List[float]:
        """Calculate growth rate percentage"""
        if len(cumulative_counts) < 2:
            return [0.0] * len(cumulative_counts)
        
        growth_rates = [0.0]  # First period has no previous data to compare
        
        for i in range(1, len(cumulative_counts)):
            if cumulative_counts[i-1] == 0:
                growth_rates.append(100.0 if cumulative_counts[i] > 0 else 0.0)
            else:
                rate = ((cumulative_counts[i] - cumulative_counts[i-1]) / cumulative_counts[i-1]) * 100
                growth_rates.append(round(rate, 2))
        
        return growth_rates

    def clear_cache(self, merchant_id: int) -> None:
        """Clear all cached analytics data for a merchant"""
        pattern = f"analytics:{merchant_id}:*"
        try:
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
        except Exception:
            pass