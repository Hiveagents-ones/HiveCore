import stripe
from typing import Dict, Any, Optional
from decimal import Decimal
from .base import PaymentGateway
from ..models.order import Order, OrderStatus
from ..models.subscription import Subscription

class StripeGateway(PaymentGateway):
    """
    Stripe支付网关实现
    支持信用卡支付、订阅支付和退款
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        stripe.api_key = config.get('api_key')
        self.webhook_secret = config.get('webhook_secret')

    async def create_payment(self, order: Order) -> Dict[str, Any]:
        """
        创建Stripe支付订单

        Args:
            order: 订单对象

        Returns:
            包含支付信息的字典
        """
        try:
            # 创建Stripe支付意图
            intent = stripe.PaymentIntent.create(
                amount=int(order.amount * 100),  # Stripe使用分为单位
                currency=order.currency.lower(),
                metadata={'order_id': str(order.id)},
                payment_method_types=['card'],
                confirmation_method='manual',
                confirm=False
            )

            return {
                'payment_id': intent.id,
                'client_secret': intent.client_secret,
                'status': intent.status,
                'amount': order.amount,
                'currency': order.currency
            }
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe payment creation failed: {str(e)}")

    async def verify_payment(self, payment_data: Dict[str, Any]) -> bool:
        """
        验证Stripe支付结果

        Args:
            payment_data: 支付回调数据

        Returns:
            支付是否成功
        """
        try:
            payment_intent_id = payment_data.get('payment_intent')
            if not payment_intent_id:
                return False

            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return intent.status == 'succeeded'
        except stripe.error.StripeError:
            return False

    async def refund_payment(self, order: Order, amount: Optional[Decimal] = None) -> bool:
        """
        处理Stripe退款

        Args:
            order: 订单对象
            amount: 退款金额

        Returns:
            退款是否成功
        """
        try:
            refund_params = {
                'payment_intent': order.payment_id
            }
            if amount:
                refund_params['amount'] = int(amount * 100)

            stripe.Refund.create(**refund_params)
            return True
        except stripe.error.StripeError:
            return False

    async def get_payment_status(self, payment_id: str) -> OrderStatus:
        """
        获取Stripe支付状态

        Args:
            payment_id: 支付ID

        Returns:
            订单状态
        """
        try:
            intent = stripe.PaymentIntent.retrieve(payment_id)
            status_mapping = {
                'requires_payment_method': OrderStatus.PENDING,
                'requires_confirmation': OrderStatus.PENDING,
                'requires_action': OrderStatus.PENDING,
                'processing': OrderStatus.PROCESSING,
                'succeeded': OrderStatus.COMPLETED,
                'canceled': OrderStatus.CANCELLED
            }
            return status_mapping.get(intent.status, OrderStatus.FAILED)
        except stripe.error.StripeError:
            return OrderStatus.FAILED

    async def process_subscription_payment(self, subscription: Subscription) -> Dict[str, Any]:
        """
        处理Stripe订阅支付

        Args:
            subscription: 订阅对象

        Returns:
            支付处理结果
        """
        try:
            # 创建Stripe客户
            customer = stripe.Customer.create(
                email=subscription.user.email,
                metadata={'user_id': str(subscription.user.id)}
            )

            # 创建订阅
            stripe_subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{'price': subscription.plan.stripe_price_id}],
                payment_behavior='default_incomplete',
                expand=['latest_invoice.payment_intent']
            )

            return {
                'subscription_id': stripe_subscription.id,
                'client_secret': stripe_subscription.latest_invoice.payment_intent.client_secret,
                'status': stripe_subscription.status
            }
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe subscription creation failed: {str(e)}")

    def get_required_config_fields(self) -> list:
        """
        获取Stripe必需的配置字段

        Returns:
            必需配置字段列表
        """
        return ['api_key', 'webhook_secret']

    def get_supported_currencies(self) -> list:
        """
        获取Stripe支持的货币列表

        Returns:
            支持的货币代码列表
        """
        return [
            'USD', 'EUR', 'GBP', 'CAD', 'AUD', 'CHF', 'SEK', 'NOK', 'DKK',
            'PLN', 'CZK', 'HUF', 'RON', 'BGN', 'HRK', 'RUB', 'TRY', 'ILS',
            'MXN', 'BRL', 'ARS', 'CLP', 'COP', 'PEN', 'UYU', 'JPY', 'SGD',
            'HKD', 'INR', 'IDR', 'MYR', 'PHP', 'THB', 'VND', 'ZAR', 'NGN',
            'GHS', 'KES', 'UGX', 'XOF', 'XAF', 'XPF', 'NZD', 'FJD', 'PGK',
            'SBD', 'TOP', 'WST', 'VUV', 'AUD', 'NAD', 'BWP', 'SZL', 'LSL',
            'ZMW', 'BND', 'KHR', 'LAK', 'MVR', 'NPR', 'LKR', 'PKR', 'AFN',
            'BDT', 'BTN', 'MGA', 'MUR', 'SCR', 'SOS', 'TZS', 'XCD', 'XOF',
            'XPF', 'CNY'
        ]

    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理Stripe webhook事件

        Args:
            webhook_data: webhook数据

        Returns:
            处理结果
        """
        try:
            event = stripe.Event.construct_from(webhook_data, stripe.api_key)

            if event.type == 'payment_intent.succeeded':
                payment_intent = event.data.object
                return {
                    'type': 'payment_success',
                    'payment_id': payment_intent.id,
                    'order_id': payment_intent.metadata.get('order_id'),
                    'amount': Decimal(payment_intent.amount) / 100,
                    'currency': payment_intent.currency.upper()
                }
            elif event.type == 'payment_intent.payment_failed':
                payment_intent = event.data.object
                return {
                    'type': 'payment_failed',
                    'payment_id': payment_intent.id,
                    'order_id': payment_intent.metadata.get('order_id')
                }
            elif event.type == 'invoice.payment_succeeded':
                invoice = event.data.object
                return {
                    'type': 'subscription_payment_success',
                    'subscription_id': invoice.subscription,
                    'amount': Decimal(invoice.amount_paid) / 100,
                    'currency': invoice.currency.upper()
                }
            elif event.type == 'invoice.payment_failed':
                invoice = event.data.object
                return {
                    'type': 'subscription_payment_failed',
                    'subscription_id': invoice.subscription
                }
            else:
                return {'type': 'unhandled_event', 'event_type': event.type}
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe webhook processing failed: {str(e)}")
