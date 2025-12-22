from typing import Dict, Any
from .base import PaymentGateway


class PaymentGatewayFactory:
    """
    支付网关工厂类，根据配置动态创建具体的支付网关实例。
    """

    _gateways: Dict[str, type] = {}

    @classmethod
    def register(cls, name: str, gateway_class: type):
        """
        注册支付网关
        :param name: 网关名称
        :param gateway_class: 网关类
        """
        if not issubclass(gateway_class, PaymentGateway):
            raise ValueError(f"Gateway class {gateway_class} must inherit from PaymentGateway")
        cls._gateways[name] = gateway_class

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> PaymentGateway:
        """
        创建支付网关实例
        :param name: 网关名称
        :param kwargs: 初始化参数
        :return: 支付网关实例
        """
        if name not in cls._gateways:
            raise ValueError(f"Unknown payment gateway: {name}")
        gateway_class = cls._gateways[name]
        return gateway_class(**kwargs)

    @classmethod
    def list_gateways(cls) -> Dict[str, type]:
        """
        获取所有已注册的支付网关
        :return: 网关字典
        """
        return cls._gateways.copy()
