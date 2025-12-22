from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from .schemas.payment import Payment, PaymentCreate, PaymentUpdate, PaymentReport
from .database import models


class PaymentService:
    def __init__(self, db: Session):
        self.db = db

    def create_payment(self, payment: PaymentCreate) -> Payment:
        """创建支付记录"""
        db_payment = models.Payment(
            member_id=payment.member_id,
            amount=payment.amount,
            payment_date=payment.payment_date,
            payment_type=payment.payment_type
        )
        self.db.add(db_payment)
        self.db.commit()
        self.db.refresh(db_payment)
        return db_payment

    def get_payment(self, payment_id: int) -> Optional[Payment]:
        """获取单个支付记录"""
        return self.db.query(models.Payment).filter(models.Payment.id == payment_id).first()

    def get_payments_by_member(self, member_id: int) -> List[Payment]:
        """获取会员的所有支付记录"""
        return self.db.query(models.Payment).filter(models.Payment.member_id == member_id).all()

    def update_payment(self, payment_id: int, payment: PaymentUpdate) -> Optional[Payment]:
        """更新支付记录"""
        db_payment = self.db.query(models.Payment).filter(models.Payment.id == payment_id).first()
        if not db_payment:
            return None
            
        if payment.member_id is not None:
            db_payment.member_id = payment.member_id
        if payment.amount is not None:
            db_payment.amount = payment.amount
        if payment.payment_date is not None:
            db_payment.payment_date = payment.payment_date
        if payment.payment_type is not None:
            db_payment.payment_type = payment.payment_type
            
        self.db.commit()
        self.db.refresh(db_payment)
        return db_payment

    def delete_payment(self, payment_id: int) -> bool:
        """删除支付记录"""
        db_payment = self.db.query(models.Payment).filter(models.Payment.id == payment_id).first()
        if not db_payment:
            return False
            
        self.db.delete(db_payment)
        self.db.commit()
        return True

    def generate_report(self, start_date: datetime, end_date: datetime) -> PaymentReport:
        """生成支付报表"""
        payments = self.db.query(models.Payment).filter(
            models.Payment.payment_date >= start_date,
            models.Payment.payment_date <= end_date
        ).all()
        
        total_amount = sum(p.amount for p in payments)
        payment_count = len(payments)
        
        return PaymentReport(
            total_amount=total_amount,
            payment_count=payment_count,
            start_date=start_date,
            end_date=end_date
        )

    def calculate_membership_fee(self, member_id: int) -> float:
        """计算会员费"""
        # 这里可以根据业务规则实现具体的会员费计算逻辑
        # 示例: 基础会员费 + 额外服务费
        return 1000.0  # 示例固定值

    def calculate_course_fee(self, course_ids: List[int]) -> float:
        """计算课程费用"""
        # 这里可以根据业务规则实现具体的课程费计算逻辑
        # 示例: 查询课程价格并求和
        courses = self.db.query(models.Course).filter(models.Course.id.in_(course_ids)).all()
        return sum(500.0 for _ in courses)  # 示例固定值