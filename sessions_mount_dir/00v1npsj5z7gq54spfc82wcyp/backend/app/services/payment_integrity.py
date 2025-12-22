from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from .database import get_db
from .models import Payment, Member, Course


class PaymentIntegrityService:
    """
    支付完整性服务，负责验证和修复支付记录
    """

    def __init__(self, db: Session = None):
        self.db = db or next(get_db())

    def verify_payment_records(self, member_id: Optional[int] = None) -> List[dict]:
        """
        验证支付记录的完整性
        :param member_id: 可选，指定会员ID时只验证该会员的记录
        :return: 返回有问题的支付记录列表
        """
        query = self.db.query(Payment)
        if member_id:
            query = query.filter(Payment.member_id == member_id)

        issues = []
        for payment in query.all():
            # 检查会员是否存在
            member = self.db.query(Member).get(payment.member_id)
            if not member:
                issues.append({
                    'payment_id': payment.id,
                    'issue': '关联会员不存在',
                    'severity': 'high'
                })
                continue

            # 检查课程支付但课程不存在的情况
            if payment.payment_type == 'course' and not self.db.query(Course).get(payment.member_id):
                issues.append({
                    'payment_id': payment.id,
                    'issue': '关联课程不存在',
                    'severity': 'medium'
                })

            # 检查金额是否为负数
            if payment.amount <= 0:
                issues.append({
                    'payment_id': payment.id,
                    'issue': '支付金额无效',
                    'severity': 'high'
                })

            # 检查支付日期是否在未来
            if payment.payment_date > datetime.now():
                issues.append({
                    'payment_id': payment.id,
                    'issue': '支付日期在未来',
                    'severity': 'medium'
                })

        return issues

    def fix_payment_issues(self, payment_id: int) -> bool:
        """
        尝试修复有问题的支付记录
        :param payment_id: 要修复的支付记录ID
        :return: 是否修复成功
        """
        payment = self.db.query(Payment).get(payment_id)
        if not payment:
            return False

        # 修复会员不存在的记录
        member = self.db.query(Member).get(payment.member_id)
        if not member:
            # 如果会员不存在，将支付记录标记为无效
            payment.status = 'invalid'
            self.db.commit()
            return True

        # 修复课程不存在的记录
        if payment.payment_type == 'course' and not self.db.query(Course).get(payment.member_id):
            # 如果课程支付但课程不存在，将支付类型改为会员费
            payment.payment_type = 'membership'
            self.db.commit()
            return True

        # 修复金额为负数的情况
        if payment.amount <= 0:
            # 设置为最小金额1元
            payment.amount = 1
            self.db.commit()
            return True

        # 修复支付日期在未来
        if payment.payment_date > datetime.now():
            # 设置为当前日期
            payment.payment_date = datetime.now()
            self.db.commit()
            return True

        return False

    def generate_integrity_report(self) -> dict:
        """
        生成支付完整性报告
        :return: 包含统计信息的报告
        """
        total_payments = self.db.query(Payment).count()
        issues = self.verify_payment_records()
        
        high_issues = [i for i in issues if i['severity'] == 'high']
        medium_issues = [i for i in issues if i['severity'] == 'medium']
        
        return {
            'total_payments': total_payments,
            'total_issues': len(issues),
            'high_priority_issues': len(high_issues),
            'medium_priority_issues': len(medium_issues),
            'integrity_score': round((total_payments - len(issues)) / total_payments * 100, 2) if total_payments > 0 else 100
        }