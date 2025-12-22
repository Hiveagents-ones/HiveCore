from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Payment, Member


class PaymentStatsService:
    """
    高精度报表计算服务，提供各种支付统计功能
    """

    def __init__(self, db: Session):
        self.db = db

    def get_daily_stats(self, start_date: str, end_date: str) -> Dict[str, float]:
        """
        获取指定日期范围内的每日支付统计
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            Dict[str, float]: 包含每日统计数据的字典，key为日期，value为当日总金额
        """
        payments = self.db.query(
            Payment.payment_date,
            Payment.amount
        ).filter(
            Payment.payment_date >= start_date,
            Payment.payment_date <= end_date
        ).all()

        df = pd.DataFrame(payments, columns=['date', 'amount'])
        df['date'] = pd.to_datetime(df['date']).dt.date
        
        if df.empty:
            return {}
            
        daily_stats = df.groupby('date')['amount'].sum().to_dict()
        return {str(date): float(amount) for date, amount in daily_stats.items()}

    def get_member_payment_stats(self, member_id: int) -> Dict[str, float]:
        """
        获取指定会员的支付统计
        
        Args:
            member_id: 会员ID
            
        Returns:
            Dict[str, float]: 包含会员统计数据的字典
                - total_amount: 总支付金额
                - last_payment_date: 最后支付日期
                - payment_count: 支付次数
        """
        payments = self.db.query(Payment).filter(
            Payment.member_id == member_id
        ).all()
        
        if not payments:
            return {
                'total_amount': 0.0,
                'last_payment_date': None,
                'payment_count': 0
            }
            
        total_amount = sum(p.amount for p in payments)
        last_payment_date = max(p.payment_date for p in payments)
        
        return {
            'total_amount': float(total_amount),
            'last_payment_date': last_payment_date,
            'payment_count': len(payments)
        }

    def get_top_paying_members(self, limit: int = 10) -> List[Dict]:
        """
        获取支付金额最高的会员列表
        
        Args:
            limit: 返回的会员数量
            
        Returns:
            List[Dict]: 包含会员信息和支付统计的字典列表
        """
        result = self.db.query(
            Member.id,
            Member.name,
            Member.email,
            Member.phone,
            Payment.amount
        ).join(
            Payment, Member.id == Payment.member_id
        ).all()
        
        df = pd.DataFrame(result, columns=['id', 'name', 'email', 'phone', 'amount'])
        
        if df.empty:
            return []
            
        top_members = df.groupby(['id', 'name', 'email', 'phone'])['amount'].sum()\
            .nlargest(limit).reset_index()
            
        return top_members.to_dict('records')

    def get_payment_method_distribution(self) -> Dict[str, float]:
        """
        获取支付方式分布统计
        
        Returns:
            Dict[str, float]: 包含支付方式分布比例的字典
        """
        payments = self.db.query(Payment.payment_method, Payment.amount).all()
        
        df = pd.DataFrame(payments, columns=['method', 'amount'])
        
        if df.empty:
            return {}
            
        distribution = df.groupby('method')['amount'].sum()
        total = distribution.sum()
        
        return {method: float(amount / total) for method, amount in distribution.items()}


# 快速使用示例
if __name__ == "__main__":
    db = next(get_db())
    service = PaymentStatsService(db)
    
    # 示例1: 获取最近7天的每日统计
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)
    print("最近7天支付统计:", service.get_daily_stats(str(start_date), str(end_date)))
    
    # 示例2: 获取支付方式分布
    print("支付方式分布:", service.get_payment_method_distribution())