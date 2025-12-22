from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from decimal import Decimal
from ..models.order import Order, OrderStatus
from ..models.subscription import Subscription

class PaymentGateway(ABC):
    """
    支付网关抽象基类，定义支付流程的统一接口
    实现策略模式，支持多种支付方式的扩展
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化支付网关
        
        Args:
            config: 支付网关配置信息
        """
        self.config = config
        self.gateway_name = self.__class__.__name__

    @abstractmethod
    async def create_payment(self, order: Order) -> Dict[str, Any]:
        """
        创建支付订单
        
        Args:
            order: 订单对象
            
        Returns:
            包含支付信息的字典，包括支付URL、支付ID等
        """
        pass

    @abstractmethod
    async def verify_payment(self, payment_data: Dict[str, Any]) -> bool:
        """
        验证支付结果
        
        Args:
            payment_data: 支付回调数据
            
        Returns:
            支付是否成功
        """
        pass

    @abstractmethod
    async def refund_payment(self, order: Order, amount: Optional[Decimal] = None) -> bool:
        """
        退款处理
        
        Args:
            order: 订单对象
            amount: 退款金额，None表示全额退款
            
        Returns:
            退款是否成功
        """
        pass

    @abstractmethod
    async def get_payment_status(self, payment_id: str) -> OrderStatus:
        """
        获取支付状态
        
        Args:
            payment_id: 支付ID
            
        Returns:
            订单状态
        """
        pass

    async def process_subscription_payment(self, subscription: Subscription) -> Dict[str, Any]:
        """
        处理订阅支付（默认实现，子类可重写）
        
        Args:
            subscription: 订阅对象
            
        Returns:
            支付处理结果
        """
        # 默认使用普通订单支付流程
        order = await subscription.get_current_order()
        return await self.create_payment(order)

    def validate_config(self) -> bool:
        """
        验证配置是否有效（默认实现，子类可重写）
        
        Returns:
            配置是否有效
        """
        required_fields = self.get_required_config_fields()
        return all(field in self.config for field in required_fields)

    def get_required_config_fields(self) -> list:
        """
        获取必需的配置字段（子类应重写）
        
        Returns:
            必需配置字段列表
        """
        return []

    def get_supported_currencies(self) -> list:
        """
        获取支持的货币列表（子类应重写）
        
        Returns:
            支持的货币代码列表
        """
        return ['USD']

    def is_currency_supported(self, currency: str) -> bool:
        """
        检查是否支持指定货币
        
        Args:
            currency: 货币代码
            
        Returns:
            是否支持该货币
        """
        return currency.upper() in self.get_supported_currencies()

    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理支付网关webhook（默认实现，子类可重写）
        
        Args:
            webhook_data: webhook数据
            
        Returns:
            处理结果
        """
        # 默认验证支付并返回结果
        is_valid = await self.verify_payment(webhook_data)
        return {
            'status': 'success' if is_valid else 'failed',
            'gateway': self.gateway_name,
            'processed': True
        }

    def get_error_message(self, error_code: str) -> str:
        """
        获取错误信息（子类可重写）
        
        Args:
            error_code: 错误代码
            
        Returns:
            错误信息
        """
        error_map = {
            'INVALID_AMOUNT': 'Invalid payment amount',
            'INVALID_CURRENCY': 'Unsupported currency',
            'PAYMENT_FAILED': 'Payment processing failed',
            'REFUND_FAILED': 'Refund processing failed',
            'INVALID_CONFIG': 'Invalid gateway configuration'
        }
        return error_map.get(error_code, 'Unknown error occurred')

    def __str__(self) -> str:
        return f"{self.gateway_name} Payment Gateway"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} config={self.config}>"
