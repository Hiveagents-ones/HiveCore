from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from ..database import get_db
from ..models import Member, Course, Payment, Report
from ..core.cache import multi_cache
from ..core.permissions import rbac, require_permission
import json
from fastapi import HTTPException

class ReportService:
    def __init__(self, db: Session):
        self.db = db
    
    @require_permission("reports", "view")
    async def get_member_trend(self, start_date: datetime, end_date: datetime, current_user: str) -> Dict[str, Any]:
        cache_key = f"member_trend:{start_date.date()}:{end_date.date()}"
        
        cached_data = multi_cache.get(cache_key)
        if cached_data:
            return cached_data
        
        # 查询每日新增会员
        daily_new = self.db.query(
            func.date(Member.created_at).label('date'),
            func.count(Member.id).label('count')
        ).filter(
            Member.created_at >= start_date,
            Member.created_at <= end_date
        ).group_by(func.date(Member.created_at)).all()
        
        # 查询会员类型分布
        member_types = self.db.query(
            Member.card_type,
            func.count(Member.id).label('count')
        ).group_by(Member.card_type).all()
        
        # 查询会员性别分布
        gender_dist = self.db.query(
            Member.gender,
            func.count(Member.id).label('count')
        ).group_by(Member.gender).all()
        
        data = {
            "daily_new": [{"date": str(d.date), "count": d.count} for d in daily_new],
            "member_types": [{"type": t.card_type, "count": t.count} for t in member_types],
            "gender_distribution": [{"gender": g.gender, "count": g.count} for g in gender_dist],
            "total_members": self.db.query(func.count(Member.id)).scalar()
        }
        
        multi_cache.set(cache_key, data, ttl=1800)  # 30分钟缓存
        return data
    
    @require_permission("reports", "view")
    async def get_course_popularity(self, start_date: datetime, end_date: datetime, current_user: str) -> Dict[str, Any]:
        cache_key = f"course_popularity:{start_date.date()}:{end_date.date()}"
        
        cached_data = multi_cache.get(cache_key)
        if cached_data:
            return cached_data
        
        # 查询课程报名人数
        course_enrollment = self.db.query(
            Course.name,
            Course.coach,
            func.count(Payment.id).label('enrollments'),
            func.sum(Payment.amount).label('revenue')
        ).join(
            Payment, Course.id == Payment.course_id
        ).filter(
            Payment.timestamp >= start_date,
            Payment.timestamp <= end_date
        ).group_by(
            Course.id, Course.name, Course.coach
        ).order_by(
            func.count(Payment.id).desc()
        ).all()
        
        # 查询时间段分布
        time_slots = self.db.query(
            extract('hour', Course.time).label('hour'),
            func.count(Payment.id).label('count')
        ).join(
            Payment, Course.id == Payment.course_id
        ).filter(
            Payment.timestamp >= start_date,
            Payment.timestamp <= end_date
        ).group_by(
            extract('hour', Course.time)
        ).order_by(
            extract('hour', Course.time)
        ).all()
        
        # 查询场地使用率
        location_usage = self.db.query(
            Course.location,
            func.count(Payment.id).label('usage')
        ).join(
            Payment, Course.id == Payment.course_id
        ).filter(
            Payment.timestamp >= start_date,
            Payment.timestamp <= end_date
        ).group_by(
            Course.location
        ).order_by(
            func.count(Payment.id).desc()
        ).all()
        
        data = {
            "course_enrollment": [
                {
                    "course_name": c.name,
                    "coach": c.coach,
                    "enrollments": c.enrollments,
                    "revenue": float(c.revenue) if c.revenue else 0
                }
                for c in course_enrollment
            ],
            "time_slots": [{"hour": int(t.hour), "count": t.count} for t in time_slots],
            "location_usage": [{"location": l.location, "usage": l.usage} for l in location_usage]
        }
        
        multi_cache.set(cache_key, data, ttl=1800)
        return data
    
    @require_permission("reports", "view")
    async def get_revenue_stats(self, start_date: datetime, end_date: datetime, current_user: str) -> Dict[str, Any]:
        cache_key = f"revenue_stats:{start_date.date()}:{end_date.date()}"
        
        cached_data = multi_cache.get(cache_key)
        if cached_data:
            return cached_data
        
        # 每日收入
        daily_revenue = self.db.query(
            func.date(Payment.timestamp).label('date'),
            func.sum(Payment.amount).label('revenue')
        ).filter(
            Payment.timestamp >= start_date,
            Payment.timestamp <= end_date
        ).group_by(
            func.date(Payment.timestamp)
        ).all()
        
        # 支付类型分布
        payment_types = self.db.query(
            Payment.type,
            func.count(Payment.id).label('count'),
            func.sum(Payment.amount).label('amount')
        ).filter(
            Payment.timestamp >= start_date,
            Payment.timestamp <= end_date
        ).group_by(
            Payment.type
        ).all()
        
        # 月度趋势
        monthly_trend = self.db.query(
            extract('year', Payment.timestamp).label('year'),
            extract('month', Payment.timestamp).label('month'),
            func.sum(Payment.amount).label('revenue')
        ).filter(
            Payment.timestamp >= start_date,
            Payment.timestamp <= end_date
        ).group_by(
            extract('year', Payment.timestamp),
            extract('month', Payment.timestamp)
        ).order_by(
            extract('year', Payment.timestamp),
            extract('month', Payment.timestamp)
        ).all()
        
        # Top会员消费
        top_members = self.db.query(
            Member.name,
            func.sum(Payment.amount).label('total_spent')
        ).join(
            Payment, Member.id == Payment.member_id
        ).filter(
            Payment.timestamp >= start_date,
            Payment.timestamp <= end_date
        ).group_by(
            Member.id, Member.name
        ).order_by(
            func.sum(Payment.amount).desc()
        ).limit(10).all()
        
        data = {
            "daily_revenue": [
                {"date": str(d.date), "revenue": float(d.revenue) if d.revenue else 0}
                for d in daily_revenue
            ],
            "payment_types": [
                {
                    "type": p.type,
                    "count": p.count,
                    "amount": float(p.amount) if p.amount else 0
                }
                for p in payment_types
            ],
            "monthly_trend": [
                {
                    "year": int(m.year),
                    "month": int(m.month),
                    "revenue": float(m.revenue) if m.revenue else 0
                }
                for m in monthly_trend
            ],
            "top_members": [
                {"name": m.name, "total_spent": float(m.total_spent) if m.total_spent else 0}
                for m in top_members
            ],
            "total_revenue": self.db.query(func.sum(Payment.amount)).filter(
                Payment.timestamp >= start_date,
                Payment.timestamp <= end_date
            ).scalar() or 0
        }
        
        multi_cache.set(cache_key, data, ttl=1800)
        return data
    
    @require_permission("reports", "export")
    async def generate_report(self, report_type: str, params: Dict[str, Any], current_user: str) -> str:
        # 生成报表任务，返回任务ID
        from ..tasks.celery_app import celery_app
        
        task = celery_app.send_task(
            'export_report',
            args=[report_type, params, current_user],
            kwargs={}
        )
        
        # 生成报表记录
        report = Report(
            type=report_type,
            data=json.dumps(params),
            generated_at=datetime.utcnow(),
            status="processing",
            task_id=task.id
        )
        self.db.add(report)
        self.db.commit()
        
        return task.id
    
    @require_permission("reports", "view")
    async def drill_down_data(self, report_type: str, filters: Dict[str, Any], current_user: str) -> List[Dict[str, Any]]:
        # 根据报表类型和过滤条件获取详细数据
        if report_type == "member_trend":
            query = self.db.query(Member)
            if filters.get("start_date"):
                query = query.filter(Member.created_at >= filters["start_date"])
            if filters.get("end_date"):
                query = query.filter(Member.created_at <= filters["end_date"])
            if filters.get("card_type"):
                query = query.filter(Member.card_type == filters["card_type"])
                
            members = query.all()
            return [
                {
                    "id": m.id,
                    "name": m.name,
                    "gender": m.gender,
                    "contact": m.contact,
                    "card_type": m.card_type,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in members
            ]
            
        elif report_type == "course_popularity":
            query = self.db.query(Course, func.count(Payment.id).label('enrollments')).join(
                Payment, Course.id == Payment.course_id
            ).group_by(Course.id)
            
            if filters.get("coach"):
                query = query.filter(Course.coach == filters["coach"])
            if filters.get("location"):
                query = query.filter(Course.location == filters["location"])
                
            courses = query.all()
            return [
                {
                    "course_id": c.id,
                    "name": c.name,
                    "coach": c.coach,
                    "location": c.location,
                    "time": c.time.isoformat() if c.time else None,
                    "enrollments": enrollments
                }
                for c, enrollments in courses
            ]
            
        elif report_type == "revenue_stats":
            query = self.db.query(Payment, Member.name.label('member_name')).join(
                Member, Payment.member_id == Member.id
            )
            
            if filters.get("start_date"):
                query = query.filter(Payment.timestamp >= filters["start_date"])
            if filters.get("end_date"):
                query = query.filter(Payment.timestamp <= filters["end_date"])
            if filters.get("payment_type"):
                query = query.filter(Payment.type == filters["payment_type"])
                
            payments = query.all()
            return [
                {
                    "id": p.id,
                    "member_name": member_name,
                    "type": p.type,
                    "amount": float(p.amount),
                    "timestamp": p.timestamp.isoformat() if p.timestamp else None
                }
                for p, member_name in payments
            ]
        
        return []
    
    async def clear_cache(self, pattern: str = None) -> bool:
        if pattern:
            return multi_cache.l2_cache.delete_pattern(pattern)
        else:
            multi_cache.clear_all()
            return True