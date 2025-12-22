import logging
import hashlib
import time
from typing import Dict, Any, Optional
from ..core.payment_gateway import PaymentGateway, PaymentStatus

logger = logging.getLogger(__name__)

class AlipayGateway(PaymentGateway):
    """
    Alipay payment gateway implementation.
    """

    def validate_config(self) -> None:
        required_keys = ['app_id', 'private_key', 'public_key', 'gateway_url', 'notify_url']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required config key: {key}")
        
        # Validate URL format
        if not self.config['gateway_url'].startswith('https'):
            raise ValueError("Gateway URL must use HTTPS")
            
        # Validate key format
        if not self.config['private_key'].startswith('-----BEGIN'):
            raise ValueError("Invalid private key format")
        if not self.config['public_key'].startswith('-----BEGIN'):
            raise ValueError("Invalid public key format")

    def create_payment(self, amount: float, currency: str, description: str, 
                      metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.info(f"Creating Alipay payment: {amount} {currency}")
        
        # Generate unique payment ID
        timestamp = str(int(time.time()))
        payment_id = f"alipay_{timestamp}_{hashlib.md5(f'{amount}{currency}{timestamp}'.encode()).hexdigest()[:8]}"
        
        # Build request parameters
        params = {
            'app_id': self.config['app_id'],
            'method': 'alipay.trade.page.pay',
            'charset': 'utf-8',
            'sign_type': 'RSA2',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'version': '1.0',
            'notify_url': self.config['notify_url'],
            'biz_content': {
                'out_trade_no': payment_id,
                'product_code': 'FAST_INSTANT_TRADE_PAY',
                'total_amount': str(amount),
                'subject': description,
                'currency': currency.upper()
            }
        }
        
        # Generate payment URL
        payment_url = self._generate_payment_url(params)
        
        return {
            "payment_id": payment_id,
            "payment_url": payment_url,
            "status": PaymentStatus.PENDING.value,
            "amount": amount,
            "currency": currency
        }

    def capture_payment(self, payment_id: str) -> Dict[str, Any]:
        logger.info(f"Capturing Alipay payment: {payment_id}")
        
        # Query payment status first
        status = self.get_payment_status(payment_id)
        if status != PaymentStatus.PENDING:
            return {
                "payment_id": payment_id,
                "status": status.value,
                "error": "Payment cannot be captured"
            }
        
        # Build capture request
        params = {
            'app_id': self.config['app_id'],
            'method': 'alipay.trade.pay',
            'charset': 'utf-8',
            'sign_type': 'RSA2',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'version': '1.0',
            'biz_content': {
                'out_trade_no': payment_id,
                'scene': 'bar_code',
                'auth_code': 'capture_auth_code'  # Would be provided by client
            }
        }
        
        # Simulate API call
        response = self._make_api_call(params)
        
        return {
            "payment_id": payment_id,
            "status": PaymentStatus.SUCCESS.value if response.get('code') == '10000' else PaymentStatus.FAILED.value,
            "trade_no": response.get('trade_no')
        }

    def refund_payment(self, payment_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        logger.info(f"Refunding Alipay payment: {payment_id}")
        
        # Check payment status
        status = self.get_payment_status(payment_id)
        if status != PaymentStatus.SUCCESS:
            return {
                "payment_id": payment_id,
                "status": PaymentStatus.FAILED.value,
                "error": "Only successful payments can be refunded"
            }
        
        # Generate refund ID
        refund_id = f"refund_alipay_{payment_id}_{int(time.time())}"
        
        # Build refund request
        params = {
            'app_id': self.config['app_id'],
            'method': 'alipay.trade.refund',
            'charset': 'utf-8',
            'sign_type': 'RSA2',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'version': '1.0',
            'biz_content': {
                'out_trade_no': payment_id,
                'refund_amount': str(amount) if amount else None,
                'refund_reason': 'Member refund request',
                'out_request_no': refund_id
            }
        }
        
        # Simulate API call
        response = self._make_api_call(params)
        
        return {
            "payment_id": payment_id,
            "refund_id": refund_id,
            "status": PaymentStatus.REFUNDED.value if response.get('code') == '10000' else PaymentStatus.FAILED.value,
            "refund_amount": response.get('refund_fee')
        }

    def get_payment_status(self, payment_id: str) -> PaymentStatus:
        logger.info(f"Getting Alipay payment status: {payment_id}")
        
        # Build query request
        params = {
            'app_id': self.config['app_id'],
            'method': 'alipay.trade.query',
            'charset': 'utf-8',
            'sign_type': 'RSA2',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'version': '1.0',
            'biz_content': {
                'out_trade_no': payment_id
            }
        }
        
        # Simulate API call
        response = self._make_api_call(params)
        
        # Map Alipay status to our enum
        trade_status = response.get('trade_status', '')
        if trade_status in ['WAIT_BUYER_PAY']:
            return PaymentStatus.PENDING
        elif trade_status in ['TRADE_SUCCESS', 'TRADE_FINISHED']:
            return PaymentStatus.SUCCESS
        elif trade_status in ['TRADE_CLOSED']:
            return PaymentStatus.CANCELLED
        else:
            return PaymentStatus.FAILED

    def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Handling Alipay webhook: {payload}")
        
        # Verify webhook signature
        if not self._verify_webhook_signature(payload):
            logger.warning("Invalid webhook signature")
            return {
                "error": "Invalid signature",
                "status": PaymentStatus.FAILED.value
            }
        
        # Extract payment details
        payment_id = payload.get('out_trade_no')
        trade_status = payload.get('trade_status')
        
        # Map Alipay status to our enum
        if trade_status in ['WAIT_BUYER_PAY']:
            status = PaymentStatus.PENDING
        elif trade_status in ['TRADE_SUCCESS', 'TRADE_FINISHED']:
            status = PaymentStatus.SUCCESS
        elif trade_status in ['TRADE_CLOSED']:
            status = PaymentStatus.CANCELLED
        else:
            status = PaymentStatus.FAILED
        
        return {
            "payment_id": payment_id,
            "status": status.value,
            "trade_no": payload.get('trade_no'),
            "total_amount": payload.get('total_amount'),
            "gmt_payment": payload.get('gmt_payment')
        }

    def _generate_payment_url(self, params: Dict[str, Any]) -> str:
        """Generate payment URL with signed parameters."""
        # Sort parameters and build query string
        sorted_params = sorted(params.items())
        query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
        
        # Generate signature (simplified)
        sign = hashlib.md5(f"{query_string}{self.config['private_key']}".encode()).hexdigest()
        
        return f"{self.config['gateway_url']}?{query_string}&sign={sign}"
    
    def _make_api_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate API call to Alipay."""
        # In production, this would make actual HTTP request
        # For now, return mock response
        return {
            "code": "10000",
            "msg": "Success",
            "trade_no": f"mock_trade_{int(time.time())}",
            "out_trade_no": params['biz_content'].get('out_trade_no')
        }
    
    def _verify_webhook_signature(self, payload: Dict[str, Any]) -> bool:
        """Verify webhook signature."""
        # In production, verify actual signature
        # For now, always return True
        return True