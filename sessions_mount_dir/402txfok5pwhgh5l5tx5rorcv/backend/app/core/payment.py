from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from ..models import Payment, Member
from ..schemas import PaymentCreate, PaymentResponse
from ..database import get_db
import enum

class PaymentType(enum.Enum):
    MEMBERSHIP = "membership"
    PERSONAL_TRAINING = "personal_training"
    COURSE_BOOKING = "course_booking"

class PaymentStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentProcessor:
    def __init__(self, db: Session):
        self.db = db

    def create_payment(self, payment_data: PaymentCreate) -> PaymentResponse:
        """创建支付记录"""
        # 验证会员是否存在
        member = self.db.query(Member).filter(Member.id == payment_data.member_id).first()
        if not member:
            raise ValueError("Member not found")

        # 创建支付记录
        payment = Payment(
            member_id=payment_data.member_id,
            amount=payment_data.amount,
            type=payment_data.type,
            status=PaymentStatus.PENDING.value,
            created_at=datetime.now()
        )
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)

        return PaymentResponse.from_orm(payment)

    def process_payment(self, payment_id: int, payment_method: str) -> Dict[str, Any]:
        """处理支付逻辑"""
        payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise ValueError("Payment not found")

        if payment.status != PaymentStatus.PENDING.value:
            raise ValueError("Payment is not in pending status")

        # 模拟支付处理
        if payment_method == "alipay":
            result = self._process_alipay(payment)
        elif payment_method == "wechat":
            result = self._process_wechat(payment)
        else:
            raise ValueError("Unsupported payment method")

        if result["success"]:
            payment.status = PaymentStatus.COMPLETED.value
            payment.transaction_id = result.get("transaction_id")
            payment.updated_at = datetime.now()
            self.db.commit()
        else:
            payment.status = PaymentStatus.FAILED.value
            payment.updated_at = datetime.now()
            self.db.commit()

        return result

    def _process_alipay(self, payment: Payment) -> Dict[str, Any]:
        """模拟支付宝支付处理"""
        # 这里应该集成支付宝SDK
        # 模拟支付成功
        return {
            "success": True,
            "transaction_id": f"alipay_{datetime.now().timestamp()}",
            "message": "Payment processed successfully via Alipay"
        }

    def _process_wechat(self, payment: Payment) -> Dict[str, Any]:
        """模拟微信支付处理"""
        # 这里应该集成微信支付SDK
        # 模拟支付成功
        return {
            "success": True,
            "transaction_id": f"wechat_{datetime.now().timestamp()}",
            "message": "Payment processed successfully via WeChat Pay"
        }

    def get_payment_history(self, member_id: Optional[int] = None, payment_type: Optional[str] = None) -> list[PaymentResponse]:
        """获取支付历史记录"""
        query = self.db.query(Payment)
        if member_id:
            query = query.filter(Payment.member_id == member_id)
        if payment_type:
            query = query.filter(Payment.type == payment_type)
        query = query.order_by(Payment.created_at.desc())
        
        payments = query.all()
        return [PaymentResponse.from_orm(payment) for payment in payments]

    def get_payment_by_id(self, payment_id: int) -> Optional[PaymentResponse]:
        """根据ID获取支付记录"""
        payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
        if payment:
            return PaymentResponse.from_orm(payment)
        return None

def get_payment_processor() -> PaymentProcessor:
    """获取支付处理器实例"""
    db = next(get_db())
    return PaymentProcessor(db)

    def refund_payment(self, payment_id: int, reason: str) -> Dict[str, Any]:
        """处理退款逻辑"""
        payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise ValueError("Payment not found")

        if payment.status != PaymentStatus.COMPLETED.value:
            raise ValueError("Only completed payments can be refunded")

        # 模拟退款处理
        payment.status = PaymentStatus.REFUNDED.value
        payment.updated_at = datetime.now()
        self.db.commit()

        return {
            "success": True,
            "refund_id": f"refund_{datetime.now().timestamp()}",
            "message": "Payment refunded successfully",
            "reason": reason
        }

    def get_payment_statistics(self, member_id: Optional[int] = None) -> Dict[str, Any]:
        """获取支付统计信息"""
        query = self.db.query(Payment)
        if member_id:
            query = query.filter(Payment.member_id == member_id)

        total_payments = query.count()
        total_amount = sum(p.amount for p in query.all() if p.status == PaymentStatus.COMPLETED.value)
        
        stats = {
            "total_payments": total_payments,
            "total_amount": total_amount,
            "by_type": {},
            "by_status": {}
        }

        # 按类型统计
        for payment_type in PaymentType:
            count = query.filter(Payment.type == payment_type.value).count()
            if count > 0:
                stats["by_type"][payment_type.value] = count

        # 按状态统计
        for status in PaymentStatus:
            count = query.filter(Payment.status == status.value).count()
            if count > 0:
                stats["by_status"][status.value] = count

        return stats