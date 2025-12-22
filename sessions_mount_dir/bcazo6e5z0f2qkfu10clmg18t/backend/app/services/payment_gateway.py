from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from datetime import datetime
import hashlib
import hmac
import json
import requests
from urllib.parse import quote_plus

from ..core.config import settings

logger = logging.getLogger(__name__)


class PaymentGatewayError(Exception):
    """支付网关异常基类"""
    pass


class PaymentResult:
    """支付结果封装类"""
    def __init__(self, success: bool, transaction_id: Optional[str] = None, 
                 gateway_response: Optional[Dict[str, Any]] = None, 
                 error_message: Optional[str] = None):
        self.success = success
        self.transaction_id = transaction_id
        self.gateway_response = gateway_response or {}
        self.error_message = error_message
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "transaction_id": self.transaction_id,
            "gateway_response": self.gateway_response,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat()
        }


class PaymentGateway(ABC):
    """支付网关抽象基类"""
    
    @abstractmethod
    async def create_payment(self, order_id: str, amount: float, 
                           currency: str, subject: str, 
                           return_url: str, notify_url: str) -> PaymentResult:
        """创建支付订单"""
        pass
    
    @abstractmethod
    async def verify_payment(self, notification_data: Dict[str, Any]) -> PaymentResult:
        """验证支付结果"""
        pass
    
    @abstractmethod
    async def query_payment(self, order_id: str) -> PaymentResult:
        """查询支付状态"""
        pass


class AlipayGateway(PaymentGateway):
    """支付宝支付网关实现"""
    
    def __init__(self):
        self.app_id = settings.ALIPAY_APP_ID
        self.private_key = settings.ALIPAY_PRIVATE_KEY
        self.public_key = settings.ALIPAY_PUBLIC_KEY
        self.gateway_url = "https://openapi.alipay.com/gateway.do"
        self.charset = "utf-8"
        self.sign_type = "RSA2"
        self.version = "1.0"
    
    def _generate_sign(self, params: Dict[str, Any]) -> str:
        """生成签名"""
        # 过滤空值并排序
        filtered_params = {k: v for k, v in params.items() if v is not None and v != ""}
        sorted_params = sorted(filtered_params.items())
        # 构造待签名字符串
        sign_string = "&".join([f"{k}={v}" for k, v in sorted_params])
        # 使用RSA2签名
        sign = hmac.new(
            self.private_key.encode(self.charset),
            sign_string.encode(self.charset),
            hashlib.sha256
        ).digest()
        return base64.b64encode(sign).decode(self.charset)
    
    async def create_payment(self, order_id: str, amount: float, 
                           currency: str, subject: str, 
                           return_url: str, notify_url: str) -> PaymentResult:
        try:
            params = {
                "app_id": self.app_id,
                "method": "alipay.trade.page.pay",
                "charset": self.charset,
                "sign_type": self.sign_type,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "version": self.version,
                "notify_url": notify_url,
                "return_url": return_url,
                "biz_content": json.dumps({
                    "out_trade_no": order_id,
                    "total_amount": f"{amount:.2f}",
                    "subject": subject,
                    "product_code": "FAST_INSTANT_TRADE_PAY"
                })
            }
            
            params["sign"] = self._generate_sign(params)
            
            # 构造支付URL
            payment_url = f"{self.gateway_url}?{quote_plus('&'.join([f'{k}={v}' for k, v in params.items()]))}"
            
            return PaymentResult(
                success=True,
                transaction_id=order_id,
                gateway_response={"payment_url": payment_url}
            )
        except Exception as e:
            logger.error(f"Alipay create payment error: {str(e)}")
            return PaymentResult(
                success=False,
                error_message=str(e)
            )
    
    async def verify_payment(self, notification_data: Dict[str, Any]) -> PaymentResult:
        try:
            # 验证签名
            sign = notification_data.get("sign")
            if not sign:
                return PaymentResult(success=False, error_message="Missing signature")
            
            # 构造待验签字符串
            params = {k: v for k, v in notification_data.items() if k != "sign" and k != "sign_type"}
            sorted_params = sorted(params.items())
            sign_string = "&".join([f"{k}={v}" for k, v in sorted_params])
            
            # 验证签名
            decoded_sign = base64.b64decode(sign)
            expected_sign = hmac.new(
                self.public_key.encode(self.charset),
                sign_string.encode(self.charset),
                hashlib.sha256
            ).digest()
            
            if not hmac.compare_digest(decoded_sign, expected_sign):
                return PaymentResult(success=False, error_message="Invalid signature")
            
            # 检查支付状态
            trade_status = notification_data.get("trade_status")
            if trade_status not in ["TRADE_SUCCESS", "TRADE_FINISHED"]:
                return PaymentResult(success=False, error_message="Payment not completed")
            
            return PaymentResult(
                success=True,
                transaction_id=notification_data.get("out_trade_no"),
                gateway_response=notification_data
            )
        except Exception as e:
            logger.error(f"Alipay verify payment error: {str(e)}")
            return PaymentResult(
                success=False,
                error_message=str(e)
            )
    
    async def query_payment(self, order_id: str) -> PaymentResult:
        try:
            params = {
                "app_id": self.app_id,
                "method": "alipay.trade.query",
                "charset": self.charset,
                "sign_type": self.sign_type,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "version": self.version,
                "biz_content": json.dumps({
                    "out_trade_no": order_id
                })
            }
            
            params["sign"] = self._generate_sign(params)
            
            response = requests.post(self.gateway_url, data=params)
            response_data = response.json()
            
            if response_data.get("code") != "10000":
                return PaymentResult(
                    success=False,
                    error_message=response_data.get("msg", "Query failed")
                )
            
            trade_status = response_data.get("trade_status")
            if trade_status not in ["TRADE_SUCCESS", "TRADE_FINISHED"]:
                return PaymentResult(
                    success=False,
                    error_message="Payment not completed"
                )
            
            return PaymentResult(
                success=True,
                transaction_id=order_id,
                gateway_response=response_data
            )
        except Exception as e:
            logger.error(f"Alipay query payment error: {str(e)}")
            return PaymentResult(
                success=False,
                error_message=str(e)
            )


class WechatGateway(PaymentGateway):
    """微信支付网关实现"""
    
    def __init__(self):
        self.app_id = settings.WECHAT_APP_ID
        self.mch_id = settings.WECHAT_MCH_ID
        self.api_key = settings.WECHAT_API_KEY
        self.gateway_url = "https://api.mch.weixin.qq.com/pay/unifiedorder"
        self.query_url = "https://api.mch.weixin.qq.com/pay/orderquery"
    
    def _generate_sign(self, params: Dict[str, Any]) -> str:
        """生成签名"""
        # 过滤空值并排序
        filtered_params = {k: v for k, v in params.items() if v is not None and v != ""}
        sorted_params = sorted(filtered_params.items())
        # 构造待签名字符串
        sign_string = "&".join([f"{k}={v}" for k, v in sorted_params])
        sign_string += f"&key={self.api_key}"
        # MD5签名
        return hashlib.md5(sign_string.encode("utf-8")).hexdigest().upper()
    
    async def create_payment(self, order_id: str, amount: float, 
                           currency: str, subject: str, 
                           return_url: str, notify_url: str) -> PaymentResult:
        try:
            params = {
                "appid": self.app_id,
                "mch_id": self.mch_id,
                "nonce_str": hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest(),
                "body": subject,
                "out_trade_no": order_id,
                "total_fee": int(amount * 100),  # 微信支付金额单位为分
                "spbill_create_ip": "127.0.0.1",
                "notify_url": notify_url,
                "trade_type": "NATIVE"  # 扫码支付
            }
            
            params["sign"] = self._generate_sign(params)
            
            # 构造XML请求
            xml_data = "<xml>"
            for k, v in params.items():
                xml_data += f"<{k}>{v}</{k}>"
            xml_data += "</xml>"
            
            response = requests.post(self.gateway_url, data=xml_data.encode("utf-8"), 
                                   headers={"Content-Type": "application/xml"})
            
            # 解析XML响应
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)
            response_data = {child.tag: child.text for child in root}
            
            if response_data.get("return_code") != "SUCCESS":
                return PaymentResult(
                    success=False,
                    error_message=response_data.get("return_msg", "Create payment failed")
                )
            
            if response_data.get("result_code") != "SUCCESS":
                return PaymentResult(
                    success=False,
                    error_message=response_data.get("err_code_des", "Create payment failed")
                )
            
            return PaymentResult(
                success=True,
                transaction_id=order_id,
                gateway_response={
                    "code_url": response_data.get("code_url"),
                    "prepay_id": response_data.get("prepay_id")
                }
            )
        except Exception as e:
            logger.error(f"Wechat create payment error: {str(e)}")
            return PaymentResult(
                success=False,
                error_message=str(e)
            )
    
    async def verify_payment(self, notification_data: Dict[str, Any]) -> PaymentResult:
        try:
            # 验证签名
            sign = notification_data.get("sign")
            if not sign:
                return PaymentResult(success=False, error_message="Missing signature")
            
            # 构造待验签字符串
            params = {k: v for k, v in notification_data.items() if k != "sign"}
            expected_sign = self._generate_sign(params)
            
            if sign != expected_sign:
                return PaymentResult(success=False, error_message="Invalid signature")
            
            # 检查支付状态
            if notification_data.get("return_code") != "SUCCESS" or \
               notification_data.get("result_code") != "SUCCESS":
                return PaymentResult(
                    success=False,
                    error_message="Payment not completed"
                )
            
            return PaymentResult(
                success=True,
                transaction_id=notification_data.get("out_trade_no"),
                gateway_response=notification_data
            )
        except Exception as e:
            logger.error(f"Wechat verify payment error: {str(e)}")
            return PaymentResult(
                success=False,
                error_message=str(e)
            )
    
    async def query_payment(self, order_id: str) -> PaymentResult:
        try:
            params = {
                "appid": self.app_id,
                "mch_id": self.mch_id,
                "out_trade_no": order_id,
                "nonce_str": hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()
            }
            
            params["sign"] = self._generate_sign(params)
            
            # 构造XML请求
            xml_data = "<xml>"
            for k, v in params.items():
                xml_data += f"<{k}>{v}</{k}>"
            xml_data += "</xml>"
            
            response = requests.post(self.query_url, data=xml_data.encode("utf-8"), 
                                   headers={"Content-Type": "application/xml"})
            
            # 解析XML响应
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)
            response_data = {child.tag: child.text for child in root}
            
            if response_data.get("return_code") != "SUCCESS":
                return PaymentResult(
                    success=False,
                    error_message=response_data.get("return_msg", "Query failed")
                )
            
            if response_data.get("result_code") != "SUCCESS":
                return PaymentResult(
                    success=False,
                    error_message=response_data.get("err_code_des", "Query failed")
                )
            
            if response_data.get("trade_state") != "SUCCESS":
                return PaymentResult(
                    success=False,
                    error_message="Payment not completed"
                )
            
            return PaymentResult(
                success=True,
                transaction_id=order_id,
                gateway_response=response_data
            )
        except Exception as e:
            logger.error(f"Wechat query payment error: {str(e)}")
            return PaymentResult(
                success=False,
                error_message=str(e)
            )


class PaymentGatewayFactory:
    """支付网关工厂类"""
    
    @staticmethod
    def create_gateway(gateway_type: str) -> PaymentGateway:
        """根据类型创建支付网关实例"""
        if gateway_type.lower() == "alipay":
            return AlipayGateway()
        elif gateway_type.lower() == "wechat":
            return WechatGateway()
        else:
            raise ValueError(f"Unsupported payment gateway type: {gateway_type}")


# 导入base64模块
import base64