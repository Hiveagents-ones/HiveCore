from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from ..schemas.payment import PaymentReport
from ..services.payment import get_payments_by_date_range
from ..database import get_db

router = APIRouter(
    prefix="/api/v1/reports",
    tags=["reports"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[PaymentReport])
async def generate_payment_report(
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db)
):
    """
    Generate payment report within a date range
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        List of payment records with member details
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        if start > end:
            raise HTTPException(status_code=400, detail="Start date cannot be after end date")
            
        if (end - start) > timedelta(days=365):
            raise HTTPException(status_code=400, detail="Date range cannot exceed 1 year")
            
        payments = get_payments_by_date_range(db, start_date=start, end_date=end)
        return payments
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

@router.get("/summary")
async def get_financial_summary(
    db: Session = Depends(get_db)
):
    """
    Get financial summary (total revenue, monthly breakdown)
    
    Returns:
        Dictionary with financial summary data
    """
    # This would be implemented with actual aggregation queries in production
    return {
        "total_revenue": 0,
        "monthly_breakdown": {},
        "membership_types": {}
    }