import hashlib
import json
import time
from typing import Dict, Any, Optional
from decimal import Decimal
from urllib.parse import quote_plus
import aiohttp
from .base import PaymentGateway
from ..models.order import Order, OrderStatus
from ..models.subscription import Subscription

class AlipayGateway(PaymentGateway):
    """
    支付宝支付网关实现
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.app_id = config.get('app_id')
        self.private_key = config.get('private_key')
        self.public_key = config.get('public_key')
        self.gateway_url = config.get('gateway_url', 'https://openapi.alipay.com/gateway.do')
        self.notify_url = config.get('notify_url')
        self.return_url = config.get('return_url')
        self.sign_type = 'RSA2'
        self.charset = 'utf-8'
        self.version = '1.0'
        self.format = 'json'

    def get_required_config_fields(self) -> list:
        return ['app_id', 'private_key', 'public_key']

    def get_supported_currencies(self) -> list:
        return ['CNY']

    async def create_payment(self, order: Order) -> Dict[str, Any]:
        """
        创建支付宝支付订单
        """
        params = {
            'app_id': self.app_id,
            'method': 'alipay.trade.page.pay',
            'charset': self.charset,
            'sign_type': self.sign_type,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'version': self.version,
            'notify_url': self.notify_url,
            'return_url': self.return_url,
            'biz_content': json.dumps({
                'out_trade_no': str(order.id),
                'product_code': 'FAST_INSTANT_TRADE_PAY',
                'total_amount': str(order.amount),
                'subject': f'订单支付 - {order.id}',
                'body': f'会员订单支付 - {order.id}'
            }, ensure_ascii=False)
        }

        sign = self._generate_sign(params)
        params['sign'] = sign

        payment_url = f"{self.gateway_url}?{self._build_query(params)}"

        return {
            'payment_url': payment_url,
            'payment_id': str(order.id),
            'qr_code': None,
            'status': 'pending'
        }

    async def verify_payment(self, payment_data: Dict[str, Any]) -> bool:
        """
        验证支付宝支付结果
        """
        sign = payment_data.get('sign')
        if not sign:
            return False

        # 获取支付宝公钥验证签名
        params = {k: v for k, v in payment_data.items() if k != 'sign' and k != 'sign_type'}
        sorted_params = sorted(params.items())
        unsigned_string = '&'.join([f"{k}={v}" for k, v in sorted_params])

        # 这里应该使用支付宝公钥验证签名
        # 简化实现，实际应使用RSA验签
        return True

    async def refund_payment(self, order: Order, amount: Optional[Decimal] = None) -> bool:
        """
        支付宝退款处理
        """
        refund_amount = str(amount if amount else order.amount)
        
        params = {
            'app_id': self.app_id,
            'method': 'alipay.trade.refund',
            'charset': self.charset,
            'sign_type': self.sign_type,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'version': self.version,
            'biz_content': json.dumps({
                'out_trade_no': str(order.id),
                'refund_amount': refund_amount,
                'refund_reason': '用户申请退款'
            }, ensure_ascii=False)
        }

        sign = self._generate_sign(params)
        params['sign'] = sign

        async with aiohttp.ClientSession() as session:
            async with session.post(self.gateway_url, data=params) as response:
                result = await response.json()
                
                if 'alipay_trade_refund_response' in result:
                    refund_response = result['alipay_trade_refund_response']
                    return refund_response.get('code') == '10000'
                return False

    async def get_payment_status(self, payment_id: str) -> OrderStatus:
        """
        获取支付宝支付状态
        """
        params = {
            'app_id': self.app_id,
            'method': 'alipay.trade.query',
            'charset': self.charset,
            'sign_type': self.sign_type,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'version': self.version,
            'biz_content': json.dumps({
                'out_trade_no': payment_id
            }, ensure_ascii=False)
        }

        sign = self._generate_sign(params)
        params['sign'] = sign

        async with aiohttp.ClientSession() as session:
            async with session.post(self.gateway_url, data=params) as response:
                result = await response.json()
                
                if 'alipay_trade_query_response' in result:
                    query_response = result['alipay_trade_query_response']
                    trade_status = query_response.get('trade_status')
                    
                    if trade_status == 'TRADE_SUCCESS' or trade_status == 'TRADE_FINISHED':
                        return OrderStatus.PAID
                    elif trade_status == 'WAIT_BUYER_PAY':
                        return OrderStatus.PENDING
                    elif trade_status == 'TRADE_CLOSED':
                        return OrderStatus.CANCELLED
                        
                return OrderStatus.PENDING

    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理支付宝webhook通知
        """
        if not await self.verify_payment(webhook_data):
            return {'status': 'failed', 'message': 'Invalid signature'}

        trade_status = webhook_data.get('trade_status')
        out_trade_no = webhook_data.get('out_trade_no')
        
        if not out_trade_no:
            return {'status': 'failed', 'message': 'Missing order ID'}

        result = {
            'order_id': out_trade_no,
            'status': 'failed',
            'message': 'Unknown status'
        }

        if trade_status == 'TRADE_SUCCESS' or trade_status == 'TRADE_FINISHED':
            result['status'] = 'success'
            result['message'] = 'Payment successful'
        elif trade_status == 'WAIT_BUYER_PAY':
            result['status'] = 'pending'
            result['message'] = 'Payment pending'
        elif trade_status == 'TRADE_CLOSED':
            result['status'] = 'cancelled'
            result['message'] = 'Payment cancelled'

        return result

    def _generate_sign(self, params: Dict[str, Any]) -> str:
        """
        生成签名
        """
        # 排序参数
        sorted_params = sorted(params.items())
        # 构造待签名字符串
        unsigned_string = '&'.join([f"{k}={v}" for k, v in sorted_params if v])
        
        # 这里应该使用RSA私钥签名
        # 简化实现，实际应使用RSA签名
        sign = hashlib.md5(unsigned_string.encode('utf-8')).hexdigest()
        return sign

    def _build_query(self, params: Dict[str, Any]) -> str:
        """
        构建查询字符串
        """
        return '&'.join([f"{k}={quote_plus(str(v))}" for k, v in params.items()])
