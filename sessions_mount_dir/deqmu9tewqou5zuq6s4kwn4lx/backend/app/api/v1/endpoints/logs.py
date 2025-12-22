from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.config import get_db
from backend.app.core.security import get_current_user
from backend.app.models.user import User
from backend.app.models.payment import Payment
from backend.app.models.membership import Membership

router = APIRouter()

@router.get("/payments", response_model=List[dict])
def get_payment_logs(
    start_date: Optional[datetime] = Query(None, description="Start date for log query"),
    end_date: Optional[datetime] = Query(None, description="End date for log query"),
    member_id: Optional[int] = Query(None, description="Filter by member ID"),
    payment_method: Optional[str] = Query(None, description="Filter by payment method"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve payment logs with optional filtering
    """
    query = db.query(Payment).join(Membership)
    
    if start_date:
        query = query.filter(Payment.created_at >= start_date)
    if end_date:
        query = query.filter(Payment.created_at <= end_date)
    if member_id:
        query = query.filter(Payment.member_id == member_id)
    if payment_method:
        query = query.filter(Payment.payment_method == payment_method)
    
    payments = query.offset(skip).limit(limit).all()
    
    return [
        {
            "id": payment.id,
            "member_id": payment.member_id,
            "member_name": payment.membership.user.full_name,
            "amount": float(payment.amount),
            "payment_method": payment.payment_method,
            "status": payment.status,
            "created_at": payment.created_at.isoformat(),
            "updated_at": payment.updated_at.isoformat() if payment.updated_at else None
        }
        for payment in payments
    ]

@router.get("/payments/stats", response_model=dict)
def get_payment_stats(
    start_date: Optional[datetime] = Query(None, description="Start date for stats"),
    end_date: Optional[datetime] = Query(None, description="End date for stats"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get payment statistics for analysis
    """
    query = db.query(Payment)
    
    if start_date:
        query = query.filter(Payment.created_at >= start_date)
    if end_date:
        query = query.filter(Payment.created_at <= end_date)
    
    total_payments = query.count()
    total_amount = query.with_entities(db.func.sum(Payment.amount)).scalar() or 0
    
    # Group by payment method
    method_stats = db.query(
        Payment.payment_method,
        db.func.count(Payment.id).label('count'),
        db.func.sum(Payment.amount).label('total')
    ).filter(
        Payment.created_at >= start_date if start_date else True,
        Payment.created_at <= end_date if end_date else True
    ).group_by(Payment.payment_method).all()
    
    # Daily stats for the last 30 days
    daily_stats = []
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    
    current_date = start_date.date()
    end_date = (end_date or datetime.utcnow()).date()
    
    while current_date <= end_date:
        day_total = db.query(db.func.sum(Payment.amount)).filter(
            db.func.date(Payment.created_at) == current_date
        ).scalar() or 0
        
        daily_stats.append({
            "date": current_date.isoformat(),
            "total": float(day_total)
        })
        current_date += timedelta(days=1)
    
    return {
        "total_payments": total_payments,
        "total_amount": float(total_amount),
        "method_breakdown": [
            {
                "method": method,
                "count": count,
                "total": float(total)
            }
            for method, count, total in method_stats
        ],
        "daily_stats": daily_stats
    }

@router.get("/memberships/expiring", response_model=List[dict])
def get_expiring_memberships(
    days: int = Query(30, ge=1, le=365, description="Days until expiration"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get memberships that are expiring within the specified number of days
    """
    expiry_date = datetime.utcnow() + timedelta(days=days)
    
    memberships = db.query(Membership).filter(
        Membership.end_date <= expiry_date,
        Membership.end_date >= datetime.utcnow(),
        Membership.is_active == True
    ).offset(skip).limit(limit).all()
    
    return [
        {
            "id": membership.id,
            "user_id": membership.user_id,
            "user_name": membership.user.full_name,
            "user_email": membership.user.email,
            "start_date": membership.start_date.isoformat(),
            "end_date": membership.end_date.isoformat(),
            "days_until_expiry": (membership.end_date - datetime.utcnow()).days,
            "last_payment": db.query(Payment)
                .filter(Payment.member_id == membership.id)
                .order_by(Payment.created_at.desc())
                .first()
        }
        for membership in memberships
    ]
