from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PaymentStatus(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PaymentMethod(Enum):
    WECHAT = "wechat"
    ALIPAY = "alipay"
    OFFLINE = "offline"

class PaymentResult:
    def __init__(self, status: PaymentStatus, transaction_id: Optional[str] = None, 
                 message: str = "", data: Optional[Dict[str, Any]] = None):
        self.status = status
        self.transaction_id = transaction_id
        self.message = message
        self.data = data or {}
        self.timestamp = datetime.utcnow()

class PaymentGateway(ABC):
    @abstractmethod
    def create_payment(self, amount: float, order_id: str, user_id: int, 
                      payment_method: PaymentMethod, **kwargs) -> PaymentResult:
        pass
    
    @abstractmethod
    def verify_payment(self, payment_data: Dict[str, Any]) -> PaymentResult:
        pass

class WechatPaymentGateway(PaymentGateway):
    def create_payment(self, amount: float, order_id: str, user_id: int, 
                      payment_method: PaymentMethod, **kwargs) -> PaymentResult:
        try:
            # Simulate WeChat payment creation
            payment_data = {
                "appid": "wx1234567890",
                "mch_id": "1234567890",
                "out_trade_no": order_id,
                "total_fee": int(amount * 100),
                "body": f"Membership renewal for user {user_id}",
                "notify_url": kwargs.get("notify_url", ""),
                "trade_type": "NATIVE"
            }
            
            # Simulate API call
            transaction_id = f"wx_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{order_id}"
            
            return PaymentResult(
                status=PaymentStatus.PENDING,
                transaction_id=transaction_id,
                message="WeChat payment created successfully",
                data={
                    "code_url": f"weixin://wxpay/bizpayurl?pr={transaction_id}",
                    "prepay_id": f"prepay_{transaction_id}"
                }
            )
        except Exception as e:
            logger.error(f"WeChat payment creation failed: {str(e)}")
            return PaymentResult(
                status=PaymentStatus.FAILED,
                message=f"WeChat payment creation failed: {str(e)}"
            )
    
    def verify_payment(self, payment_data: Dict[str, Any]) -> PaymentResult:
        try:
            # Simulate payment verification
            if payment_data.get("result_code") == "SUCCESS":
                return PaymentResult(
                    status=PaymentStatus.SUCCESS,
                    transaction_id=payment_data.get("transaction_id"),
                    message="Payment verified successfully"
                )
            else:
                return PaymentResult(
                    status=PaymentStatus.FAILED,
                    message="Payment verification failed"
                )
        except Exception as e:
            logger.error(f"WeChat payment verification failed: {str(e)}")
            return PaymentResult(
                status=PaymentStatus.FAILED,
                message=f"Payment verification failed: {str(e)}"
            )

class AlipayPaymentGateway(PaymentGateway):
    def create_payment(self, amount: float, order_id: str, user_id: int, 
                      payment_method: PaymentMethod, **kwargs) -> PaymentResult:
        try:
            # Simulate Alipay payment creation
            payment_data = {
                "app_id": "2021001234567890",
                "method": "alipay.trade.page.pay",
                "charset": "utf-8",
                "sign_type": "RSA2",
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "version": "1.0",
                "notify_url": kwargs.get("notify_url", ""),
                "biz_content": {
                    "out_trade_no": order_id,
                    "total_amount": str(amount),
                    "subject": f"Membership renewal for user {user_id}",
                    "product_code": "FAST_INSTANT_TRADE_PAY"
                }
            }
            
            # Simulate API call
            transaction_id = f"ali_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{order_id}"
            
            return PaymentResult(
                status=PaymentStatus.PENDING,
                transaction_id=transaction_id,
                message="Alipay payment created successfully",
                data={
                    "pay_url": f"https://openapi.alipay.com/gateway.do?{transaction_id}",
                    "form_data": payment_data
                }
            )
        except Exception as e:
            logger.error(f"Alipay payment creation failed: {str(e)}")
            return PaymentResult(
                status=PaymentStatus.FAILED,
                message=f"Alipay payment creation failed: {str(e)}"
            )
    
    def verify_payment(self, payment_data: Dict[str, Any]) -> PaymentResult:
        try:
            # Simulate payment verification
            if payment_data.get("trade_status") == "TRADE_SUCCESS":
                return PaymentResult(
                    status=PaymentStatus.SUCCESS,
                    transaction_id=payment_data.get("trade_no"),
                    message="Payment verified successfully"
                )
            else:
                return PaymentResult(
                    status=PaymentStatus.FAILED,
                    message="Payment verification failed"
                )
        except Exception as e:
            logger.error(f"Alipay payment verification failed: {str(e)}")
            return PaymentResult(
                status=PaymentStatus.FAILED,
                message=f"Payment verification failed: {str(e)}"
            )

class OfflinePaymentGateway(PaymentGateway):
    def create_payment(self, amount: float, order_id: str, user_id: int, 
                      payment_method: PaymentMethod, **kwargs) -> PaymentResult:
        try:
            # Offline payment doesn't require actual payment gateway
            transaction_id = f"offline_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{order_id}"
            
            return PaymentResult(
                status=PaymentStatus.PENDING,
                transaction_id=transaction_id,
                message="Offline payment created, waiting for admin confirmation",
                data={
                    "payment_instructions": "Please contact administrator to confirm payment",
                    "admin_note": kwargs.get("admin_note", "")
                }
            )
        except Exception as e:
            logger.error(f"Offline payment creation failed: {str(e)}")
            return PaymentResult(
                status=PaymentStatus.FAILED,
                message=f"Offline payment creation failed: {str(e)}"
            )
    
    def verify_payment(self, payment_data: Dict[str, Any]) -> PaymentResult:
        # Offline payment verification is done by admin
        if payment_data.get("admin_confirmed", False):
            return PaymentResult(
                status=PaymentStatus.SUCCESS,
                transaction_id=payment_data.get("transaction_id"),
                message="Offline payment confirmed by admin"
            )
        else:
            return PaymentResult(
                status=PaymentStatus.PENDING,
                message="Offline payment pending admin confirmation"
            )

class PaymentGatewayFactory:
    _gateways = {
        PaymentMethod.WECHAT: WechatPaymentGateway,
        PaymentMethod.ALIPAY: AlipayPaymentGateway,
        PaymentMethod.OFFLINE: OfflinePaymentGateway
    }
    
    @classmethod
    def get_gateway(cls, payment_method: PaymentMethod) -> PaymentGateway:
        gateway_class = cls._gateways.get(payment_method)
        if not gateway_class:
            raise ValueError(f"Unsupported payment method: {payment_method}")
        return gateway_class()
    
    @classmethod
    def create_payment(cls, amount: float, order_id: str, user_id: int, 
                      payment_method: PaymentMethod, **kwargs) -> PaymentResult:
        gateway = cls.get_gateway(payment_method)
        return gateway.create_payment(amount, order_id, user_id, payment_method, **kwargs)
    
    @classmethod
    def verify_payment(cls, payment_method: PaymentMethod, 
                      payment_data: Dict[str, Any]) -> PaymentResult:
        gateway = cls.get_gateway(payment_method)
        return gateway.verify_payment(payment_data)

# Service class for payment operations
class PaymentService:
    def __init__(self):
        self.factory = PaymentGatewayFactory
    
    def process_payment(self, amount: float, order_id: str, user_id: int, 
                       payment_method: str, **kwargs) -> PaymentResult:
        try:
            method = PaymentMethod(payment_method.lower())
            return self.factory.create_payment(amount, order_id, user_id, method, **kwargs)
        except ValueError as e:
            logger.error(f"Invalid payment method: {payment_method}")
            return PaymentResult(
                status=PaymentStatus.FAILED,
                message=f"Invalid payment method: {payment_method}"
            )
        except Exception as e:
            logger.error(f"Payment processing failed: {str(e)}")
            return PaymentResult(
                status=PaymentStatus.FAILED,
                message=f"Payment processing failed: {str(e)}"
            )
    
    def confirm_payment(self, payment_method: str, 
                       payment_data: Dict[str, Any]) -> PaymentResult:
        try:
            method = PaymentMethod(payment_method.lower())
            return self.factory.verify_payment(method, payment_data)
        except ValueError as e:
            logger.error(f"Invalid payment method: {payment_method}")
            return PaymentResult(
                status=PaymentStatus.FAILED,
                message=f"Invalid payment method: {payment_method}"
            )
        except Exception as e:
            logger.error(f"Payment confirmation failed: {str(e)}")
            return PaymentResult(
                status=PaymentStatus.FAILED,
                message=f"Payment confirmation failed: {str(e)}"
            )
    
    def get_supported_methods(self) -> list:
        return [method.value for method in PaymentMethod]

# Global payment service instance
payment_service = PaymentService()