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

class PaymentGateway(ABC):
    """支付网关抽象基类"""
    
    @abstractmethod
    def create_payment(self, order_id: str, amount: float, currency: str, 
                      description: str, return_url: str, notify_url: str, 
                      **kwargs) -> Dict[str, Any]:
        """创建支付订单
        
        Args:
            order_id: 商户订单号
            amount: 支付金额
            currency: 货币类型
            description: 支付描述
            return_url: 支付成功返回URL
            notify_url: 异步通知URL
            **kwargs: 其他参数
            
        Returns:
            Dict: 包含支付信息的字典
        """
        pass
    
    @abstractmethod
    def verify_payment(self, order_id: str, **kwargs) -> Dict[str, Any]:
        """验证支付结果
        
        Args:
            order_id: 商户订单号
            **kwargs: 其他参数
            
        Returns:
            Dict: 包含支付验证结果的字典
        """
        pass
    
    @abstractmethod
    def query_payment(self, order_id: str) -> Dict[str, Any]:
        """查询支付状态
        
        Args:
            order_id: 商户订单号
            
        Returns:
            Dict: 包含支付状态的字典
        """
        pass
    
    @abstractmethod
    def refund_payment(self, order_id: str, amount: float, reason: str) -> Dict[str, Any]:
        """申请退款
        
        Args:
            order_id: 商户订单号
            amount: 退款金额
            reason: 退款原因
            
        Returns:
            Dict: 包含退款结果的字典
        """
        pass

class WeChatPayGateway(PaymentGateway):
    """微信支付实现"""
    
    def __init__(self, app_id: str, mch_id: str, api_key: str):
        self.app_id = app_id
        self.mch_id = mch_id
        self.api_key = api_key
    
    def create_payment(self, order_id: str, amount: float, currency: str, 
                      description: str, return_url: str, notify_url: str, 
                      **kwargs) -> Dict[str, Any]:
        logger.info(f"Creating WeChat payment for order {order_id}")
        # 模拟微信支付创建订单
        return {
            "payment_id": f"wx_{order_id}_{int(datetime.now().timestamp())}",
            "payment_url": f"https://pay.weixin.qq.com/mock/pay?order_id={order_id}",
            "qr_code": f"data:image/png;base64,mock_qr_code_{order_id}",
            "status": PaymentStatus.PENDING.value,
            "expires_at": "2024-12-31T23:59:59Z"
        }
    
    def verify_payment(self, order_id: str, **kwargs) -> Dict[str, Any]:
        logger.info(f"Verifying WeChat payment for order {order_id}")
        # 模拟验证支付
        return {
            "order_id": order_id,
            "status": PaymentStatus.SUCCESS.value,
            "transaction_id": f"wx_trans_{order_id}",
            "paid_at": datetime.utcnow().isoformat(),
            "amount": kwargs.get("amount", 0)
        }
    
    def query_payment(self, order_id: str) -> Dict[str, Any]:
        logger.info(f"Querying WeChat payment status for order {order_id}")
        # 模拟查询支付状态
        return {
            "order_id": order_id,
            "status": PaymentStatus.SUCCESS.value,
            "transaction_id": f"wx_trans_{order_id}",
            "paid_at": datetime.utcnow().isoformat()
        }
    
    def refund_payment(self, order_id: str, amount: float, reason: str) -> Dict[str, Any]:
        logger.info(f"Processing WeChat refund for order {order_id}")
        # 模拟退款
        return {
            "refund_id": f"wx_refund_{order_id}",
            "status": "processing",
            "amount": amount,
            "reason": reason
        }

class AlipayGateway(PaymentGateway):
    """支付宝支付实现"""
    
    def __init__(self, app_id: str, private_key: str, public_key: str):
        self.app_id = app_id
        self.private_key = private_key
        self.public_key = public_key
    
    def create_payment(self, order_id: str, amount: float, currency: str, 
                      description: str, return_url: str, notify_url: str, 
                      **kwargs) -> Dict[str, Any]:
        logger.info(f"Creating Alipay payment for order {order_id}")
        # 模拟支付宝创建订单
        return {
            "payment_id": f"ali_{order_id}_{int(datetime.now().timestamp())}",
            "payment_url": f"https://openapi.alipay.com/gateway.do?mock=true&order_id={order_id}",
            "qr_code": f"data:image/png;base64,mock_alipay_qr_{order_id}",
            "status": PaymentStatus.PENDING.value,
            "expires_at": "2024-12-31T23:59:59Z"
        }
    
    def verify_payment(self, order_id: str, **kwargs) -> Dict[str, Any]:
        logger.info(f"Verifying Alipay payment for order {order_id}")
        # 模拟验证支付
        return {
            "order_id": order_id,
            "status": PaymentStatus.SUCCESS.value,
            "transaction_id": f"ali_trans_{order_id}",
            "paid_at": datetime.utcnow().isoformat(),
            "amount": kwargs.get("amount", 0)
        }
    
    def query_payment(self, order_id: str) -> Dict[str, Any]:
        logger.info(f"Querying Alipay payment status for order {order_id}")
        # 模拟查询支付状态
        return {
            "order_id": order_id,
            "status": PaymentStatus.SUCCESS.value,
            "transaction_id": f"ali_trans_{order_id}",
            "paid_at": datetime.utcnow().isoformat()
        }
    
    def refund_payment(self, order_id: str, amount: float, reason: str) -> Dict[str, Any]:
        logger.info(f"Processing Alipay refund for order {order_id}")
        # 模拟退款
        return {
            "refund_id": f"ali_refund_{order_id}",
            "status": "processing",
            "amount": amount,
            "reason": reason
        }

class PaymentGatewayFactory:
    """支付网关工厂类"""
    
    _gateways = {
        "wechat": WeChatPayGateway,
        "alipay": AlipayGateway
    }
    
    @classmethod
    def create_gateway(cls, gateway_type: str, **config) -> PaymentGateway:
        """创建支付网关实例
        
        Args:
            gateway_type: 网关类型 (wechat/alipay)
            **config: 网关配置参数
            
        Returns:
            PaymentGateway: 支付网关实例
            
        Raises:
            ValueError: 不支持的网关类型
        """
        if gateway_type not in cls._gateways:
            raise ValueError(f"Unsupported payment gateway: {gateway_type}")
        
        gateway_class = cls._gateways[gateway_type]
        return gateway_class(**config)
    
    @classmethod
    def register_gateway(cls, name: str, gateway_class: type):
        """注册新的支付网关
        
        Args:
            name: 网关名称
            gateway_class: 网关类
        """
        if not issubclass(gateway_class, PaymentGateway):
            raise ValueError("Gateway class must inherit from PaymentGateway")
        cls._gateways[name] = gateway_class
    
    @classmethod
    def get_available_gateways(cls) -> list:
        """获取所有可用的支付网关
        
        Returns:
            list: 网关名称列表
        """
        return list(cls._gateways.keys())

# 支付服务类，提供统一的支付接口
class PaymentService:
    """支付服务类"""
    
    def __init__(self):
        self._gateways: Dict[str, PaymentGateway] = {}
    
    def add_gateway(self, name: str, gateway: PaymentGateway):
        """添加支付网关
        
        Args:
            name: 网关名称
            gateway: 网关实例
        """
        self._gateways[name] = gateway
    
    def get_gateway(self, name: str) -> Optional[PaymentGateway]:
        """获取支付网关
        
        Args:
            name: 网关名称
            
        Returns:
            PaymentGateway: 网关实例或None
        """
        return self._gateways.get(name)
    
    def process_payment(self, gateway_name: str, order_id: str, amount: float, 
                       currency: str, description: str, return_url: str, 
                       notify_url: str, **kwargs) -> Dict[str, Any]:
        """处理支付
        
        Args:
            gateway_name: 网关名称
            order_id: 订单号
            amount: 金额
            currency: 货币
            description: 描述
            return_url: 返回URL
            notify_url: 通知URL
            **kwargs: 其他参数
            
        Returns:
            Dict: 支付结果
        """
        gateway = self.get_gateway(gateway_name)
        if not gateway:
            raise ValueError(f"Payment gateway '{gateway_name}' not found")
        
        return gateway.create_payment(
            order_id=order_id,
            amount=amount,
            currency=currency,
            description=description,
            return_url=return_url,
            notify_url=notify_url,
            **kwargs
        )
    
    def verify_payment(self, gateway_name: str, order_id: str, **kwargs) -> Dict[str, Any]:
        """验证支付
        
        Args:
            gateway_name: 网关名称
            order_id: 订单号
            **kwargs: 其他参数
            
        Returns:
            Dict: 验证结果
        """
        gateway = self.get_gateway(gateway_name)
        if not gateway:
            raise ValueError(f"Payment gateway '{gateway_name}' not found")
        
        return gateway.verify_payment(order_id=order_id, **kwargs)

# 全局支付服务实例
payment_service = PaymentService()

# 初始化默认支付网关
def init_payment_gateways(config: Dict[str, Dict[str, Any]]):
    """初始化支付网关
    
    Args:
        config: 网关配置字典
            {
                "wechat": {"app_id": "...", "mch_id": "...", "api_key": "..."},
                "alipay": {"app_id": "...", "private_key": "...", "public_key": "..."}
            }
    """
    for gateway_name, gateway_config in config.items():
        try:
            gateway = PaymentGatewayFactory.create_gateway(gateway_name, **gateway_config)
            payment_service.add_gateway(gateway_name, gateway)
            logger.info(f"Initialized payment gateway: {gateway_name}")
        except Exception as e:
            logger.error(f"Failed to initialize payment gateway {gateway_name}: {str(e)}")