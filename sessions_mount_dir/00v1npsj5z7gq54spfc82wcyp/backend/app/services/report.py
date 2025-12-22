from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..schemas.payment import PaymentReport
from ..database import models


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def generate_payment_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        payment_type: Optional[str] = None
    ) -> PaymentReport:
        """
        Generate payment report for given date range and payment type
        
        Args:
            start_date: Start date of the report period (default: 30 days ago)
            end_date: End date of the report period (default: now)
            payment_type: Type of payment to filter (membership/course)
            
        Returns:
            PaymentReport: Report containing total amount and payment count
        """
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
            
        # Build query
        query = self.db.query(models.Payment).filter(
            models.Payment.payment_date >= start_date,
            models.Payment.payment_date <= end_date
        )
        
        # Apply payment type filter if provided
        if payment_type:
            query = query.filter(models.Payment.payment_type == payment_type)
            
        # Calculate report data using SQL aggregation
        result = query.with_entities(
            func.sum(models.Payment.amount).label('total_amount'),
            func.count(models.Payment.id).label('payment_count')
        ).first()
        total_amount = result.total_amount or 0
        payment_count = result.payment_count or 0
        
        return PaymentReport(
            total_amount=total_amount,
            payment_count=payment_count,
            start_date=start_date,
            end_date=end_date
        )

    def get_payment_types(self) -> List[str]:
    def generate_detailed_payment_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        payment_type: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[dict]:
        """
        Generate paginated detailed payment report with optimized query
        
        Args:
            start_date: Start date of the report period
            end_date: End date of the report period
            payment_type: Type of payment to filter
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List[dict]: List of payment records with details
        """
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
            
        query = self.db.query(
            models.Payment.id,
            models.Payment.member_id,
            models.Payment.amount,
            models.Payment.payment_date,
            models.Payment.payment_type
        ).filter(
            models.Payment.payment_date >= start_date,
            models.Payment.payment_date <= end_date
        )
        
        if payment_type:
            query = query.filter(models.Payment.payment_type == payment_type)
            
        payments = query.order_by(models.Payment.payment_date.desc())\
                      .limit(limit)\
                      .offset(offset)\
                      .all()
                      
        return [dict(p._asdict()) for p in payments]
        """
        Get all available payment types
        
        Returns:
            List[str]: List of unique payment types
        """
        results = self.db.query(models.Payment.payment_type).distinct().all()
        return [r[0] for r in results if r[0]]