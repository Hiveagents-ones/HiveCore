from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PaymentStatus(Enum):
    """Payment status enumeration."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentGateway(ABC):
    """
    Abstract base class for payment gateways.
    
    This class defines the interface that all payment gateway implementations
    must follow, ensuring consistent behavior across different payment providers.
    """

    """
    Abstract base class for payment gateways.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.validate_config()
    
    @abstractmethod
    def validate_config(self) -> None:
        """Validate gateway configuration.
        
        Raises:
            ValueError: If required configuration is missing or invalid.
        """

        """Validate gateway configuration."""
        pass
    
    @abstractmethod
    def create_payment(self, amount: float, currency: str, description: str, 
        """Create a payment intent.
        
        Args:
            amount: Payment amount
            currency: Currency code (e.g., 'USD', 'EUR')
            description: Payment description
            metadata: Additional payment metadata
            
        Returns:
            Dictionary containing payment details including payment_id
        """

                      metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a payment intent."""
        pass
    
    @abstractmethod
    def capture_payment(self, payment_id: str) -> Dict[str, Any]:
        """Capture a payment.
        
        Args:
            payment_id: The payment ID to capture
            
        Returns:
            Dictionary containing capture result
        """

        """Capture a payment."""
        pass
    
    @abstractmethod
    def refund_payment(self, payment_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        """Refund a payment.
        
        Args:
            payment_id: The payment ID to refund
            amount: Refund amount (None for full refund)
            
        Returns:
            Dictionary containing refund details
        """

        """Refund a payment."""
        pass
    
    @abstractmethod
    def get_payment_status(self, payment_id: str) -> PaymentStatus:
        """Get payment status.
        
        Args:
            payment_id: The payment ID to check
            
        Returns:
            Current payment status
        """

        """Get payment status."""
        pass
    
    @abstractmethod
    def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle webhook notifications.
        
        Args:
            payload: Webhook payload from payment provider
            
        Returns:
            Processed webhook event details
        """

        """Handle webhook notifications."""
        pass

class StripeGateway(PaymentGateway):
    """
    Stripe payment gateway implementation.
    """
    
    def validate_config(self) -> None:
        required_keys = ['secret_key', 'publishable_key', 'webhook_secret']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required config key: {key}")
    
    def create_payment(self, amount: float, currency: str, description: str, 
                      metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Mock implementation - replace with actual Stripe SDK calls
        logger.info(f"Creating Stripe payment: {amount} {currency}")
        return {
            "payment_id": f"pi_stripe_{amount}_{currency}",
            "client_secret": "pi_stripe_secret",
            "status": PaymentStatus.PENDING.value
        }
    
    def capture_payment(self, payment_id: str) -> Dict[str, Any]:
        logger.info(f"Capturing Stripe payment: {payment_id}")
        return {
            "payment_id": payment_id,
            "status": PaymentStatus.SUCCESS.value
        }
    
    def refund_payment(self, payment_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        logger.info(f"Refunding Stripe payment: {payment_id}")
        return {
            "payment_id": payment_id,
            "refund_id": f"re_stripe_{payment_id}",
            "status": PaymentStatus.REFUNDED.value
        }
    
    def get_payment_status(self, payment_id: str) -> PaymentStatus:
        # Mock implementation - replace with actual Stripe SDK calls
        return PaymentStatus.SUCCESS
    
    def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Handling Stripe webhook")
        return {
            "event_type": payload.get("type"),
            "payment_id": payload.get("data", {}).get("object", {}).get("id"),
            "status": PaymentStatus.SUCCESS.value
        }

class PayPalGateway(PaymentGateway):


class AlipayGateway(PaymentGateway):
    """
    Alipay payment gateway implementation.
    """

    def validate_config(self) -> None:
        required_keys = ['app_id', 'private_key', 'public_key']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required config key: {key}")

    def create_payment(self, amount: float, currency: str, description: str, 
                      metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.info(f"Creating Alipay payment: {amount} {currency}")
        return {
            "payment_id": f"pay_alipay_{amount}_{currency}",
            "payment_url": "https://openapi.alipay.com/gateway.do",
            "status": PaymentStatus.PENDING.value
        }

    def capture_payment(self, payment_id: str) -> Dict[str, Any]:
        logger.info(f"Capturing Alipay payment: {payment_id}")
        return {
            "payment_id": payment_id,
            "status": PaymentStatus.SUCCESS.value
        }

    def refund_payment(self, payment_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        logger.info(f"Refunding Alipay payment: {payment_id}")
        return {
            "payment_id": payment_id,
            "refund_id": f"re_alipay_{payment_id}",
            "status": PaymentStatus.REFUNDED.value
        }

    def get_payment_status(self, payment_id: str) -> PaymentStatus:
        return PaymentStatus.SUCCESS

    def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Handling Alipay webhook")
        return {
            "event_type": payload.get("trade_status"),
            "payment_id": payload.get("out_trade_no"),
            "status": PaymentStatus.SUCCESS.value
        }


class WeChatGateway(PaymentGateway):
    """
    WeChat Pay payment gateway implementation.
    """

    def validate_config(self) -> None:
        required_keys = ['app_id', 'mch_id', 'api_key']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required config key: {key}")

    def create_payment(self, amount: float, currency: str, description: str, 
                      metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.info(f"Creating WeChat payment: {amount} {currency}")
        return {
            "payment_id": f"pay_wechat_{amount}_{currency}",
            "code_url": "weixin://wxpay/bizpayurl",
            "status": PaymentStatus.PENDING.value
        }

    def capture_payment(self, payment_id: str) -> Dict[str, Any]:
        logger.info(f"Capturing WeChat payment: {payment_id}")
        return {
            "payment_id": payment_id,
            "status": PaymentStatus.SUCCESS.value
        }

    def refund_payment(self, payment_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        logger.info(f"Refunding WeChat payment: {payment_id}")
        return {
            "payment_id": payment_id,
            "refund_id": f"re_wechat_{payment_id}",
            "status": PaymentStatus.REFUNDED.value
        }

    def get_payment_status(self, payment_id: str) -> PaymentStatus:
        return PaymentStatus.SUCCESS

    def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Handling WeChat webhook")
        return {
            "event_type": payload.get("result_code"),
            "payment_id": payload.get("out_trade_no"),
            "status": PaymentStatus.SUCCESS.value
        }
    """
    PayPal payment gateway implementation.
    """
    
    def validate_config(self) -> None:
        required_keys = ['client_id', 'client_secret', 'webhook_id']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required config key: {key}")
    
    def create_payment(self, amount: float, currency: str, description: str, 
                      metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.info(f"Creating PayPal payment: {amount} {currency}")
        return {
            "payment_id": f"pay_paypal_{amount}_{currency}",
            "approval_url": "https://paypal.com/approve",
            "status": PaymentStatus.PENDING.value
        }
    
    def capture_payment(self, payment_id: str) -> Dict[str, Any]:
        logger.info(f"Capturing PayPal payment: {payment_id}")
        return {
            "payment_id": payment_id,
            "status": PaymentStatus.SUCCESS.value
        }
    
    def refund_payment(self, payment_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        logger.info(f"Refunding PayPal payment: {payment_id}")
        return {
            "payment_id": payment_id,
            "refund_id": f"re_paypal_{payment_id}",
            "status": PaymentStatus.REFUNDED.value
        }
    
    def get_payment_status(self, payment_id: str) -> PaymentStatus:
        return PaymentStatus.SUCCESS
    
    def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Handling PayPal webhook")
        return {
            "event_type": payload.get("event_type"),
            "payment_id": payload.get("resource", {}).get("id"),
            "status": PaymentStatus.SUCCESS.value
        }

class PaymentGatewayFactory:
    """
    Factory class for creating payment gateway instances.
    
    This factory implements the Factory pattern to manage and create
    different payment gateway implementations dynamically.
    """

    """
    Factory class for creating payment gateway instances.
    """
    
    _gateways = {
        "stripe": StripeGateway,
        "paypal": PayPalGateway,
        "alipay": AlipayGateway,
        "wechat": WeChatGateway
    }
    
    @classmethod
    def register_gateway(cls, name: str, gateway_class: type) -> None:
        """Register a new payment gateway.
        
        Args:
            name: Gateway name identifier
            gateway_class: Gateway implementation class
            
        Raises:
            ValueError: If gateway_class doesn't inherit from PaymentGateway
        """

        """Register a new payment gateway."""
        if not issubclass(gateway_class, PaymentGateway):
            raise ValueError("Gateway class must inherit from PaymentGateway")
        cls._gateways[name] = gateway_class
    
    @classmethod
    def create_gateway(cls, name: str, config: Dict[str, Any]) -> PaymentGateway:
        """Create a payment gateway instance.
        
        Args:
            name: Gateway name identifier
            config: Gateway configuration dictionary
            
        Returns:
            Configured payment gateway instance
            
        Raises:
            ValueError: If gateway name is not registered
        """

        """Create a payment gateway instance."""
        if name not in cls._gateways:
            raise ValueError(f"Unknown payment gateway: {name}")
        return cls._gateways[name](config)
    
    @classmethod
    def list_gateways(cls) -> list:
        """List all registered gateways.
        
        Returns:
            List of registered gateway names
        """

        """List all registered gateways."""
        return list(cls._gateways.keys())

# Default configuration for development
DEFAULT_GATEWAY_CONFIG = {
    "stripe": {
        "secret_key": "sk_test_...",
        "publishable_key": "pk_test_...",
        "webhook_secret": "whsec_..."
    },
    "paypal": {
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "webhook_id": "test_webhook_id"
    },
    "alipay": {
        "app_id": "test_app_id",
        "private_key": "test_private_key",
        "public_key": "test_public_key"
    },
    "wechat": {
        "app_id": "test_app_id",
        "mch_id": "test_mch_id",
        "api_key": "test_api_key"
    }
}

def get_gateway(gateway_name: str, config: Optional[Dict[str, Any]] = None) -> PaymentGateway:
    """Get a configured payment gateway instance.
    
    Args:
        gateway_name: Name of the gateway to create
        config: Optional configuration (uses default if None)
        
    Returns:
        Configured payment gateway instance
    """

    """Get a configured payment gateway instance."""
    if config is None:
        config = DEFAULT_GATEWAY_CONFIG.get(gateway_name, {})
    return PaymentGatewayFactory.create_gateway(gateway_name, config)


class PaymentTransaction:
    """Represents a payment transaction with metadata."""
    
    def __init__(self, payment_id: str, amount: float, currency: str,
                 status: PaymentStatus, gateway: str,
                 created_at: Optional[datetime] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        self.payment_id = payment_id
        self.amount = amount
        self.currency = currency
        self.status = status
        self.gateway = gateway
        self.created_at = created_at or datetime.utcnow()
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary."""
        return {
            "payment_id": self.payment_id,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status.value,
            "gateway": self.gateway,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }


class PaymentProcessor:
    """High-level payment processing interface."""
    
    def __init__(self, gateway: PaymentGateway):
        self.gateway = gateway
        self.transactions: Dict[str, PaymentTransaction] = {}
    
    def process_payment(self, amount: float, currency: str, description: str,
                       metadata: Optional[Dict[str, Any]] = None) -> PaymentTransaction:
        """Process a new payment."""
        result = self.gateway.create_payment(amount, currency, description, metadata)
        transaction = PaymentTransaction(
            payment_id=result["payment_id"],
            amount=amount,
            currency=currency,
            status=PaymentStatus(result["status"]),
            gateway=self.gateway.__class__.__name__,
            metadata=metadata
        )
        self.transactions[transaction.payment_id] = transaction
        return transaction
    
    def get_transaction(self, payment_id: str) -> Optional[PaymentTransaction]:
        """Retrieve a transaction by ID."""
        return self.transactions.get(payment_id)
    
    def update_transaction_status(self, payment_id: str) -> bool:
        """Update transaction status from gateway."""
        if payment_id not in self.transactions:
            return False
        
        status = self.gateway.get_payment_status(payment_id)
        self.transactions[payment_id].status = status
        return True
