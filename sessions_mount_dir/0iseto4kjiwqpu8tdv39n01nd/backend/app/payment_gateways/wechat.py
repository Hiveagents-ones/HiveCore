import hashlib
import time
import uuid
from typing import Dict, Any, Optional
from decimal import Decimal
import xml.etree.ElementTree as ET
from urllib.parse import quote
import requests

from .base import PaymentGateway
from ..models.order import Order, OrderStatus
from ..models.subscription import Subscription


class WechatPay(PaymentGateway):
    """
    微信支付网关实现
    支持JSAPI、Native、H5等支付方式
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.app_id = config.get('app_id')
        self.mch_id = config.get('mch_id')
        self.api_key = config.get('api_key')
        self.notify_url = config.get('notify_url')
        self.trade_type = config.get('trade_type', 'NATIVE')  # 默认扫码支付
        self.api_url = 'https://api.mch.weixin.qq.com/pay/unifiedorder'

    def get_required_config_fields(self) -> list:
        return ['app_id', 'mch_id', 'api_key', 'notify_url']

    def get_supported_currencies(self) -> list:
        return ['CNY']

    def _generate_sign(self, params: Dict[str, Any]) -> str:
        """
        生成微信支付签名
        """
        # 过滤空值并排序
        filtered_params = {k: v for k, v in params.items() if v != '' and v is not None}
        sorted_params = sorted(filtered_params.items(), key=lambda x: x[0])
        
        # 拼接字符串
        string_to_sign = '&'.join([f'{k}={v}' for k, v in sorted_params])
        string_to_sign += f'&key={self.api_key}'
        
        # MD5加密并转为大写
        return hashlib.md5(string_to_sign.encode('utf-8')).hexdigest().upper()

    def _create_xml(self, params: Dict[str, Any]) -> str:
        """
        创建XML请求体
        """
        xml = '<xml>'
        for k, v in params.items():
            xml += f'<{k}>{v}</{k}>'
        xml += '</xml>'
        return xml

    def _parse_xml(self, xml_str: str) -> Dict[str, Any]:
        """
        解析XML响应
        """
        root = ET.fromstring(xml_str)
        return {child.tag: child.text for child in root}

    async def create_payment(self, order: Order) -> Dict[str, Any]:
        """
        创建微信支付订单
        """
        if not self.is_currency_supported(order.currency):
            raise ValueError(f'Currency {order.currency} is not supported')

        # 构造请求参数
        params = {
            'appid': self.app_id,
            'mch_id': self.mch_id,
            'nonce_str': str(uuid.uuid4()).replace('-', ''),
            'body': f'订单支付-{order.id}',
            'out_trade_no': str(order.id),
            'total_fee': int(order.amount * 100),  # 微信支付金额单位为分
            'spbill_create_ip': '127.0.0.1',  # 实际应用中应获取真实IP
            'notify_url': self.notify_url,
            'trade_type': self.trade_type,
        }

        # 如果是JSAPI支付，需要openid
        if self.trade_type == 'JSAPI':
            params['openid'] = order.user_openid  # 假设订单中有用户openid

        # 生成签名
        params['sign'] = self._generate_sign(params)

        # 发送请求
        xml_data = self._create_xml(params)
        headers = {'Content-Type': 'application/xml'}
        response = requests.post(self.api_url, data=xml_data.encode('utf-8'), headers=headers)
        response_data = self._parse_xml(response.text)

        # 验证响应
        if response_data.get('return_code') != 'SUCCESS':
            raise Exception(f'WeChat Pay API error: {response_data.get("return_msg")}')

        if response_data.get('result_code') != 'SUCCESS':
            raise Exception(f'WeChat Pay error: {response_data.get("err_code_des")}')

        # 验证签名
        if not self._verify_sign(response_data):
            raise Exception('Invalid response signature')

        # 根据支付类型返回不同数据
        result = {
            'payment_id': response_data.get('prepay_id'),
            'order_id': order.id,
            'gateway': 'wechat',
        }

        if self.trade_type == 'NATIVE':
            result['qr_code'] = response_data.get('code_url')
        elif self.trade_type == 'JSAPI':
            # 返回JSAPI支付参数
            jsapi_params = {
                'appId': self.app_id,
                'timeStamp': str(int(time.time())),
                'nonceStr': str(uuid.uuid4()).replace('-', ''),
                'package': f'prepay_id={response_data.get("prepay_id")}',
                'signType': 'MD5',
            }
            jsapi_params['paySign'] = self._generate_sign(jsapi_params)
            result['jsapi_params'] = jsapi_params
        elif self.trade_type == 'H5':
            result['mweb_url'] = response_data.get('mweb_url')

        return result

    async def verify_payment(self, payment_data: Dict[str, Any]) -> bool:
        """
        验证微信支付回调
        """
        # 验证签名
        if not self._verify_sign(payment_data):
            return False

        # 检查支付状态
        return payment_data.get('return_code') == 'SUCCESS' and payment_data.get('result_code') == 'SUCCESS'

    async def refund_payment(self, order: Order, amount: Optional[Decimal] = None) -> bool:
        """
        微信支付退款
        """
        refund_amount = amount if amount else order.amount
        
        params = {
            'appid': self.app_id,
            'mch_id': self.mch_id,
            'nonce_str': str(uuid.uuid4()).replace('-', ''),
            'out_trade_no': str(order.id),
            'out_refund_no': f'refund_{order.id}_{int(time.time())}',
            'total_fee': int(order.amount * 100),
            'refund_fee': int(refund_amount * 100),
        }
        
        params['sign'] = self._generate_sign(params)
        
        # 发送退款请求
        xml_data = self._create_xml(params)
        headers = {'Content-Type': 'application/xml'}
        response = requests.post('https://api.mch.weixin.qq.com/secapi/pay/refund', 
                                data=xml_data.encode('utf-8'), 
                                headers=headers,
                                cert=(self.config.get('cert_path'), self.config.get('key_path')))  # 需要证书
        
        response_data = self._parse_xml(response.text)
        
        return response_data.get('return_code') == 'SUCCESS' and response_data.get('result_code') == 'SUCCESS'

    async def get_payment_status(self, payment_id: str) -> OrderStatus:
        """
        查询微信支付订单状态
        """
        params = {
            'appid': self.app_id,
            'mch_id': self.mch_id,
            'out_trade_no': payment_id,
            'nonce_str': str(uuid.uuid4()).replace('-', ''),
        }
        
        params['sign'] = self._generate_sign(params)
        
        xml_data = self._create_xml(params)
        headers = {'Content-Type': 'application/xml'}
        response = requests.post('https://api.mch.weixin.qq.com/pay/orderquery', 
                                data=xml_data.encode('utf-8'), 
                                headers=headers)
        
        response_data = self._parse_xml(response.text)
        
        if response_data.get('trade_state') == 'SUCCESS':
            return OrderStatus.PAID
        elif response_data.get('trade_state') == 'CLOSED':
            return OrderStatus.CANCELLED
        elif response_data.get('trade_state') == 'REFUND':
            return OrderStatus.REFUNDED
        else:
            return OrderStatus.PENDING

    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理微信支付webhook
        """
        # 验证签名
        if not self._verify_sign(webhook_data):
            return {'status': 'fail', 'message': 'Invalid signature'}
        
        # 处理支付结果
        if webhook_data.get('result_code') == 'SUCCESS':
            return {
                'status': 'success',
                'order_id': webhook_data.get('out_trade_no'),
                'transaction_id': webhook_data.get('transaction_id'),
                'paid_at': webhook_data.get('time_end'),
                'amount': Decimal(webhook_data.get('total_fee')) / 100,
            }
        
        return {'status': 'fail', 'message': webhook_data.get('err_code_des', 'Unknown error')}

    def _verify_sign(self, data: Dict[str, Any]) -> bool:
        """
        验证微信支付签名
        """
        sign = data.get('sign')
        if not sign:
            return False
        
        # 重新计算签名
        calculated_sign = self._generate_sign({k: v for k, v in data.items() if k != 'sign'})
        return calculated_sign == sign

    async def process_subscription_payment(self, subscription: Subscription) -> Dict[str, Any]:
        """
        处理订阅支付
        """
        # 微信支付不支持自动续费，需要用户手动支付
        order = await subscription.get_current_order()
        return await self.create_payment(order)
