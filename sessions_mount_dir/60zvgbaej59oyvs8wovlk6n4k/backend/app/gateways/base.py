from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class PaymentGateway(ABC):
    """
    支付网关的抽象基类，规定所有支付方式必须实现的接口。
    """

    @abstractmethod
    def create_payment(self, amount: float, currency: str, payment_method_id: str, **kwargs) -> Dict[str, Any]:
        """
        创建支付
        :param amount: 支付金额
        :param currency: 货币类型
        :param payment_method_id: 支付方式ID
        :param kwargs: 其他参数
        :return: 支付结果
        """
        pass

    @abstractmethod
    def confirm_payment(self, payment_intent_id: str) -> Dict[str, Any]:
        """
        确认支付
        :param payment_intent_id: 支付意图ID
        :return: 支付结果
        """
        pass

    @abstractmethod
    def cancel_payment(self, payment_intent_id: str) -> Dict[str, Any]:
        """
        取消支付
        :param payment_intent_id: 支付意图ID
        :return: 取消结果
        """
        pass

    @abstractmethod
    def retrieve_payment(self, payment_intent_id: str) -> Dict[str, Any]:
        """
        获取支付详情
        :param payment_intent_id: 支付意图ID
        :return: 支付详情
        """
        pass

    @abstractmethod
    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        处理支付网关的webhook事件
        :param payload: 请求体
        :param headers: 请求头
        :return: 处理结果
        """
        pass
