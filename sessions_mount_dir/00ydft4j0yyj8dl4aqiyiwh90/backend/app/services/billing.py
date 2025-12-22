from datetime import datetime
from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from .database import get_db
from .models.payment import Payment
from .models.member import Member


class BillingService:
    """
    计费服务核心逻辑
    处理会员卡/私教课等费用计算、支付及发票生成
    """

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def calculate_membership_fee(
        self, 
        member_id: int, 
        membership_type: str, 
        duration_months: int
    ) -> float:
        """
        计算会员卡费用
        
        Args:
            member_id: 会员ID
            membership_type: 会员类型 (basic/premium/vip)
            duration_months: 会员时长(月)
            
        Returns:
            计算后的总费用
        """
        base_prices = {
        # 会员折扣验证
        member = self.db.query(Member).filter(Member.id == member_id).first()
        if not member:
            raise ValueError(f"Member not found with ID: {member_id}")
        
        # 老会员额外折扣
        membership_duration = (datetime.now() - member.join_date).days / 30  # 转换为月数
        if membership_duration > 24:
            total *= 0.85  # 85折
        elif membership_duration > 12:
            total *= 0.9  # 9折
            "basic": 300,
            "premium": 500,
            "vip": 800
        }
        
        if membership_type not in base_prices:
            raise ValueError(f"Invalid membership type: {membership_type}")
            
        base_price = base_prices[membership_type]
        total = base_price * duration_months
        
        # 长期会员折扣
        if duration_months >= 12:
            total *= 0.9  # 9折
        elif duration_months >= 6:
            total *= 0.95  # 95折
            
        return round(total, 2)

    def calculate_course_fee(
        self, 
        course_id: int, 
        session_count: int, 
        is_private: bool = False
    ) -> float:
        """
        计算私教课程费用
        
        Args:
            course_id: 课程ID
            session_count: 课程节数
            is_private: 是否私教课程
            
        Returns:
            计算后的总费用
        """
        base_price = 200 if is_private else 100
        # 课包过期验证
        if session_count > 20:
            raise ValueError("Maximum session count per package is 20")
        
        # 私教课有效期验证
        if is_private and session_count > 10:
            raise ValueError("Maximum private session count per package is 10")
        total = base_price * session_count
        
        # 批量购买折扣
        if session_count >= 10:
            total *= 0.85  # 85折
        elif session_count >= 5:
            total *= 0.9  # 9折
            
        return round(total, 2)

    def create_payment(
        self, 
        member_id: int, 
        amount: float, 
        payment_method: str,
        description: Optional[str] = None
    ) -> Payment:
        """
        创建支付记录
        
        Args:
            member_id: 会员ID
            amount: 支付金额
            payment_method: 支付方式 (wechat/alipay/card/cash)
            description: 支付描述
            
        Returns:
            创建的支付记录
        """
        valid_methods = ["wechat", "alipay", "card", "cash"]
        if payment_method not in valid_methods:
            raise ValueError(f"Invalid payment method: {payment_method}")
            
        payment = Payment(
            member_id=member_id,
            amount=amount,
            payment_date=datetime.now(),
            payment_method=payment_method,
            description=description
        )
        
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        
        return payment

    def generate_invoice(self, payment_id: int) -> dict:
        """
        生成发票信息
        
        Args:
            payment_id: 支付ID
            
        Returns:
            包含发票信息的字典
        """
        payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise ValueError(f"Payment not found with ID: {payment_id}")
            
        return {
            "invoice_id": f"INV-{payment_id:08d}",
            "payment_id": payment.id,
            "member_id": payment.member_id,
            "amount": payment.amount,
            "payment_date": payment.payment_date,
            "payment_method": payment.payment_method,
            "invoice_date": datetime.now().date(),
            "tax_number": "1234567890"  # 示例税号
        }

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
        base_prices = {
            "basic": 300,
            "premium": 500,
            "vip": 800
        }

        if membership_type not in base_prices:
            raise ValueError(f"Invalid membership type: {membership_type}")

        base_price = base_prices[membership_type]
        total = base_price * duration_months

        # 会员折扣验证
        member = self.db.query(Member).filter(Member.id == member_id).first()
        if not member:
            raise ValueError(f"Member not found with ID: {member_id}")

        # 老会员额外折扣
        membership_duration = (datetime.now() - member.join_date).days / 30  # 转换为月数
        if membership_duration > 24:
            total *= 0.85  # 85折
        elif membership_duration > 12:
            total *= 0.9  # 9折

        # 长期会员折扣
        if duration_months >= 12:
            total *= 0.9  # 9折
        elif duration_months >= 6:
            total *= 0.95  # 95折

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
        base_prices = {
            "basic": 300,
            "premium": 500,
            "vip": 800
        }

        if membership_type not in base_prices:
            raise ValueError(f"Invalid membership type: {membership_type}")

        base_price = base_prices[membership_type]
        total = base_price * duration_months

        # 会员折扣验证
        member = self.db.query(Member).filter(Member.id == member_id).first()
        if not member:
            raise ValueError(f"Member not found with ID: {member_id}")

        # 老会员额外折扣
        membership_duration = (datetime.now() - member.join_date).days / 30  # 转换为月数
        if membership_duration > 24:
            total *= 0.85  # 85折
        elif membership_duration > 12:
            total *= 0.9  # 9折