from typing import Optional, Dict, List
from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .models import Payment, Refund, Invoice
from .schemas import PaymentCreate, RefundCreate, InvoiceCreate

logger = logging.getLogger(__name__)


class PaymentGateway(ABC):
    """支付网关抽象基类"""
    
    @abstractmethod
    def process_payment(self, amount: float, currency: str, **kwargs) -> bool:
        """处理支付"""
        pass
    
    @abstractmethod
    def process_refund(self, transaction_id: str, amount: float, **kwargs) -> bool:
        """处理退款"""
        pass
    
    @abstractmethod
    def get_payment_status(self, transaction_id: str) -> Dict:
        """获取支付状态"""
        pass


class WechatPaymentGateway(PaymentGateway):
    """微信支付网关实现"""
    
    def process_payment(self, amount: float, currency: str, **kwargs) -> bool:
        # 实际项目中这里会调用微信支付API
        return True
    
    def process_refund(self, transaction_id: str, amount: float, **kwargs) -> bool:
        # 实际项目中这里会调用微信退款API
        return True
    
    def get_payment_status(self, transaction_id: str) -> Dict:
        # 实际项目中这里会查询微信支付状态
        return {"status": "success"}


class AlipayPaymentGateway(PaymentGateway):
    """支付宝支付网关实现"""
    
    def process_payment(self, amount: float, currency: str, **kwargs) -> bool:
        # 实际项目中这里会调用支付宝API
        return True
    
    def process_refund(self, transaction_id: str, amount: float, **kwargs) -> bool:
        # 实际项目中这里会调用支付宝退款API
        return True
    
    def get_payment_status(self, transaction_id: str) -> Dict:
        # 实际项目中这里会查询支付宝支付状态
        return {"status": "success"}


class PaymentGatewayFactory:
    """支付网关工厂类"""
    
    @staticmethod
    def create_gateway(channel: PaymentChannel) -> PaymentGateway:
        """根据支付渠道创建对应的支付网关"""
        gateways = {
            PaymentChannel.WECHAT: WechatPaymentGateway(),
            PaymentChannel.ALIPAY: AlipayPaymentGateway(),
            PaymentChannel.UNIONPAY: None,  # 实际项目中需要实现
            PaymentChannel.BANK_TRANSFER: None,  # 实际项目中需要实现
            PaymentChannel.CASH: None  # 实际项目中需要实现
        }
        return gateways.get(channel)


class PaymentChannel(str, Enum):
    """支持的支付渠道枚举"""
    """支持的支付渠道枚举"""
    WECHAT = "wechat"
    ALIPAY = "alipay"
    UNIONPAY = "unionpay"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"


class PaymentRouter:
    """支付渠道路由器，根据业务规则选择最优支付渠道"""
    """支付渠道路由器，根据业务规则选择最优支付渠道"""

    @staticmethod
    def select_channel(
        amount: float,
        currency: str,
        member_id: Optional[int] = None
    ) -> PaymentChannel:
        """
        根据业务规则选择最优支付渠道
        :param amount: 支付金额
        :param currency: 货币类型
        :param member_id: 会员ID（可选）
        :return: 最优支付渠道
        """
        # 默认规则：
        # 1. 金额小于100元优先使用微信/支付宝
        # 2. 大额支付优先使用银行转账
        # 3. 会员可享受更多支付渠道
        
        if amount < 100:
            return PaymentChannel.WECHAT  # 默认微信支付
        elif amount >= 1000:
            return PaymentChannel.BANK_TRANSFER
        else:
            return PaymentChannel.ALIPAY


class PaymentStatus(str, Enum):
    """支付状态枚举"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentService:
    """支付核心服务类（增强版）
    
    新增功能：
    - 支持多渠道路由选择
    - 支持优先渠道列表
    - 支持货币类型适配
    """
    """支付核心服务类"""

    @staticmethod
    def create_payment(
        db: Session,
        payment_data: PaymentCreate,
        channel: Optional[PaymentChannel] = None,
        member_id: Optional[int] = None,
        preferred_channels: Optional[List[PaymentChannel]] = None
    ) -> Payment:
        """
        创建支付记录
        # 如果未指定支付渠道，则自动选择最优渠道
        if channel is None:
            channel = PaymentRouter.select_channel(
                amount=payment_data.amount,
                currency=payment_data.currency,
                member_id=member_id,
                preferred_channels=preferred_channels
            )
            
        # 验证支付渠道是否可用
        available_channels = {c["value"] for c in PaymentService.get_available_channels()}
        if channel not in available_channels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported payment channel: {channel}"
            )
        :param db: 数据库会话
        :param payment_data: 支付数据
        :param channel: 支付渠道
        :param member_id: 会员ID
        :return: 支付记录
        """
        try:
            payment = Payment(
                amount=payment_data.amount,
                currency=payment_data.currency,
                channel=channel,
                status=PaymentStatus.PENDING,
                member_id=member_id,
                description=payment_data.description,
                created_at=datetime.utcnow()
            )
            db.add(payment)
            db.commit()
            db.refresh(payment)
            logger.info(f"Payment created: {payment.id}")
            return payment
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create payment: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create payment"
            )

    @staticmethod
    def process_payment(
        db: Session,
        payment_id: int,
        channel_data: Optional[Dict] = None
    ) -> Payment:
        """
        处理支付（通过支付网关）
        :param db: 数据库会话
        :param payment_id: 支付ID
        :param channel_data: 渠道特定数据
        :return: 更新后的支付记录
        """
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )

        if payment.status != PaymentStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment already processed"
            )

        try:
            # 通过支付网关工厂获取对应渠道的支付网关
            gateway = PaymentGatewayFactory.create_gateway(payment.channel)
            if not gateway:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unsupported payment channel"
                )

            # 调用支付网关处理支付
            success = gateway.process_payment(
                amount=payment.amount,
                currency=payment.currency,
                **channel_data or {}
            )

            if success:
                payment.status = PaymentStatus.SUCCESS
                payment.paid_at = datetime.utcnow()
                payment.channel_data = channel_data or {}
                db.commit()
                db.refresh(payment)
                logger.info(f"Payment processed successfully: {payment.id}")
                return payment
            else:
                payment.status = PaymentStatus.FAILED
                db.commit()
                logger.warning(f"Payment processing failed: {payment.id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Payment processing failed"
                )
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to process payment: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process payment"
            )

    @staticmethod
    def create_refund(
        db: Session,
        payment_id: int,
        refund_data: RefundCreate
    ) -> Refund:
        """
        创建退款记录
        :param db: 数据库会话
        :param payment_id: 支付ID
        :param refund_data: 退款数据
        :return: 退款记录
        """
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )

        if payment.status != PaymentStatus.SUCCESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only successful payments can be refunded"
            )

        if refund_data.amount > payment.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refund amount cannot exceed payment amount"
            )

        try:
            refund = Refund(
                payment_id=payment_id,
                amount=refund_data.amount,
                reason=refund_data.reason,
                status="pending",
                created_at=datetime.utcnow()
            )
            db.add(refund)
            
            # 更新支付状态为已退款（如果是全额退款）
            if refund_data.amount == payment.amount:
                payment.status = PaymentStatus.REFUNDED
            
            db.commit()
            db.refresh(refund)
            logger.info(f"Refund created: {refund.id}")
            return refund
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create refund: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create refund"
            )

    @staticmethod
    def generate_invoice(
        db: Session,
        payment_id: int,
        invoice_data: InvoiceCreate
    ) -> Invoice:
        """
        生成发票
        :param db: 数据库会话
        :param payment_id: 支付ID
        :param invoice_data: 发票数据
        :return: 发票记录
        """
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )

        if payment.status != PaymentStatus.SUCCESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only successful payments can generate invoices"
            )

        try:
            invoice = Invoice(
                payment_id=payment_id,
                title=invoice_data.title,
                amount=payment.amount,
                tax_number=invoice_data.tax_number,
                content=invoice_data.content,
                issued_at=datetime.utcnow()
            )
            db.add(invoice)
            db.commit()
            db.refresh(invoice)
            logger.info(f"Invoice generated: {invoice.id}")
            return invoice
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to generate invoice: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate invoice"
            )

    @staticmethod
    def get_available_channels() -> List[Dict[str, str]]:
        """
        获取可用支付渠道
        :return: 支付渠道列表
        """
        """
        获取可用支付渠道
        :return: 支付渠道列表
        """
        return [
            {"name": "微信支付", "value": PaymentChannel.WECHAT},
            {"name": "支付宝", "value": PaymentChannel.ALIPAY},
            {"name": "银联支付", "value": PaymentChannel.UNIONPAY},
            {"name": "银行转账", "value": PaymentChannel.BANK_TRANSFER},
            {"name": "现金支付", "value": PaymentChannel.CASH},
        ]

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
class PaymentRouter:
    """支付渠道路由器，根据业务规则选择最优支付渠道"""

    @staticmethod
    def select_channel(
        amount: float,
        currency: str,
        member_id: Optional[int] = None,
        preferred_channels: Optional[List[PaymentChannel]] = None
    ) -> PaymentChannel:
        """
        根据业务规则选择最优支付渠道
        :param amount: 支付金额
        :param currency: 货币类型
        :param member_id: 会员ID（可选）
        :param preferred_channels: 优先渠道列表（可选）
        :return: 最优支付渠道
        """
        # 1. 如果有优先渠道列表，从中选择第一个可用的
        if preferred_channels:
            for channel in preferred_channels:
                if channel in [PaymentChannel.WECHAT, PaymentChannel.ALIPAY, PaymentChannel.UNIONPAY]:
                    return channel

        # 2. 根据金额和货币类型选择
        if currency == 'CNY':
            if amount < 100:
                return PaymentChannel.WECHAT
            elif amount >= 1000:
                return PaymentChannel.BANK_TRANSFER
            else:
                return PaymentChannel.ALIPAY
        elif currency == 'USD':
            return PaymentChannel.BANK_TRANSFER
        
        # 3. 会员专属渠道
        if member_id:
            return PaymentChannel.UNIONPAY
            
        # 默认返回微信支付
        return PaymentChannel.WECHAT

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
class PaymentRouter:
    """支付渠道路由器，根据业务规则选择最优支付渠道"""

    @staticmethod
    def select_channel(
        amount: float,
        currency: str,
        member_id: Optional[int] = None,
        preferred_channels: Optional[List[PaymentChannel]] = None
    ) -> PaymentChannel:
        """
        根据业务规则选择最优支付渠道
        :param amount: 支付金额
        :param currency: 货币类型
        :param member_id: 会员ID（可选）
        :param preferred_channels: 优先渠道列表（可选）
        :return: 最优支付渠道
        """
        # 1. 如果有优先渠道列表，从中选择第一个可用的
        if preferred_channels:
            for channel in preferred_channels:
                if channel in [PaymentChannel.WECHAT, PaymentChannel.ALIPAY, PaymentChannel.UNIONPAY]:
                    return channel

        # 2. 根据金额和货币类型选择
        if currency == 'CNY':
            if amount < 100:
                return PaymentChannel.WECHAT
            elif amount >= 1000:
                return PaymentChannel.BANK_TRANSFER
            else:
                return PaymentChannel.ALIPAY
        elif currency == 'USD':
            return PaymentChannel.BANK_TRANSFER

        # 3. 会员专属渠道
        if member_id:
            return PaymentChannel.UNIONPAY

        # 默认返回微信支付
        return PaymentChannel.WECHAT