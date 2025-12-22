import pytest
import asyncio
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.core.database import get_db
from backend.app.models.base import Base
from backend.app.models.payment import PaymentOrder, PaymentTransaction, PaymentMethod, PaymentStatus
from backend.app.schemas.payment import PaymentOrderCreate, PaymentTransactionCreate

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture
def test_user_id():
    return uuid4()


@pytest.fixture
def test_order_data(test_user_id):
    return {
        "user_id": test_user_id,
        "amount": 10000,  # 100.00 in cents
        "currency": "USD",
        "payment_method": PaymentMethod.STRIPE,
        "description": "Test payment order"
    }


class TestPaymentAPI:
    def test_create_payment_order_success(self, test_order_data):
        """Test successful payment order creation"""
        response = client.post("/api/v1/payments/orders", json=test_order_data)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(test_order_data["user_id"])
        assert data["amount"] == test_order_data["amount"]
        assert data["currency"] == test_order_data["currency"]
        assert data["status"] == PaymentStatus.PENDING
        assert "id" in data
        assert "created_at" in data

    def test_create_payment_order_invalid_method(self, test_order_data):
        """Test payment order creation with invalid payment method"""
        test_order_data["payment_method"] = "INVALID_METHOD"
        response = client.post("/api/v1/payments/orders", json=test_order_data)
        assert response.status_code == 422

    def test_get_payment_order_success(self, test_order_data):
        """Test successful payment order retrieval"""
        # Create order first
        create_response = client.post("/api/v1/payments/orders", json=test_order_data)
        order_id = create_response.json()["id"]

        # Get order
        response = client.get(f"/api/v1/payments/orders/{order_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == order_id
        assert data["user_id"] == str(test_order_data["user_id"])

    def test_get_payment_order_not_found(self):
        """Test payment order retrieval with non-existent ID"""
        fake_id = uuid4()
        response = client.get(f"/api/v1/payments/orders/{fake_id}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Payment order not found"

    def test_get_user_payment_orders(self, test_order_data, test_user_id):
        """Test retrieving all payment orders for a user"""
        # Create multiple orders
        for _ in range(3):
            client.post("/api/v1/payments/orders", json=test_order_data)

        # Get user orders
        response = client.get(f"/api/v1/payments/orders/user/{test_user_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        for order in data:
            assert order["user_id"] == str(test_user_id)

    def test_initiate_payment_success(self, test_order_data):
        """Test successful payment initiation"""
        # Create order
        create_response = client.post("/api/v1/payments/orders", json=test_order_data)
        order_id = create_response.json()["id"]

        # Initiate payment
        response = client.post(f"/api/v1/payments/orders/{order_id}/pay")
        assert response.status_code == 200
        data = response.json()
        assert "payment_url" in data or "client_secret" in data

    def test_initiate_payment_order_not_found(self):
        """Test payment initiation with non-existent order"""
        fake_id = uuid4()
        response = client.post(f"/api/v1/payments/orders/{fake_id}/pay")
        assert response.status_code == 404

    def test_payment_webhook_stripe_success(self, test_order_data):
        """Test successful Stripe webhook processing"""
        # Create and pay order
        create_response = client.post("/api/v1/payments/orders", json=test_order_data)
        order_id = create_response.json()["id"]
        client.post(f"/api/v1/payments/orders/{order_id}/pay")

        # Simulate webhook
        webhook_data = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "metadata": {"order_id": str(order_id)},
                    "amount": test_order_data["amount"]
                }
            }
        }
        response = client.post(
            "/api/v1/payments/webhook/stripe",
            json=webhook_data,
            headers={"stripe-signature": "test_signature"}
        )
        assert response.status_code == 200

        # Verify order status
        order_response = client.get(f"/api/v1/payments/orders/{order_id}")
        assert order_response.json()["status"] == PaymentStatus.SUCCEEDED

    def test_payment_webhook_invalid_signature(self, test_order_data):
        """Test webhook with invalid signature"""
        webhook_data = {"type": "payment_intent.succeeded"}
        response = client.post(
            "/api/v1/payments/webhook/stripe",
            json=webhook_data,
            headers={"stripe-signature": "invalid_signature"}
        )
        assert response.status_code == 400

    def test_refund_payment_success(self, test_order_data):
        """Test successful payment refund"""
        # Create and complete payment
        create_response = client.post("/api/v1/payments/orders", json=test_order_data)
        order_id = create_response.json()["id"]
        client.post(f"/api/v1/payments/orders/{order_id}/pay")

        # Process webhook to mark as succeeded
        webhook_data = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "metadata": {"order_id": str(order_id)},
                    "amount": test_order_data["amount"]
                }
            }
        }
        client.post(
            "/api/v1/payments/webhook/stripe",
            json=webhook_data,
            headers={"stripe-signature": "test_signature"}
        )

        # Create refund
        refund_data = {
            "order_id": order_id,
            "amount": test_order_data["amount"],
            "reason": "Customer requested refund"
        }
        response = client.post("/api/v1/payments/refunds", json=refund_data)
        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == str(order_id)
        assert data["amount"] == test_order_data["amount"]
        assert data["status"] == "PENDING"

    def test_refund_payment_order_not_succeeded(self, test_order_data):
        """Test refund for order that hasn't succeeded"""
        create_response = client.post("/api/v1/payments/orders", json=test_order_data)
        order_id = create_response.json()["id"]

        refund_data = {
            "order_id": order_id,
            "amount": test_order_data["amount"],
            "reason": "Test refund"
        }
        response = client.post("/api/v1/payments/refunds", json=refund_data)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_concurrent_payment_creation(self, test_order_data, test_user_id):
        """Test concurrent payment order creation"""
        async def create_order():
            return client.post("/api/v1/payments/orders", json=test_order_data)

        # Create 10 orders concurrently
        tasks = [create_order() for _ in range(10)]
        responses = await asyncio.gather(*tasks)

        # Verify all succeeded
        for response in responses:
            assert response.status_code == 200

        # Verify all orders exist
        user_orders = client.get(f"/api/v1/payments/orders/user/{test_user_id}")
        assert len(user_orders.json()) == 10

    def test_payment_order_amount_validation(self, test_order_data):
        """Test payment order amount validation"""
        # Test negative amount
        test_order_data["amount"] = -1000
        response = client.post("/api/v1/payments/orders", json=test_order_data)
        assert response.status_code == 422

        # Test zero amount
        test_order_data["amount"] = 0
        response = client.post("/api/v1/payments/orders", json=test_order_data)
        assert response.status_code == 422

        # Test valid amount
        test_order_data["amount"] = 10000
        response = client.post("/api/v1/payments/orders", json=test_order_data)
        assert response.status_code == 200

    def test_payment_order_currency_validation(self, test_order_data):
        """Test payment order currency validation"""
        # Test invalid currency
        test_order_data["currency"] = "INVALID"
        response = client.post("/api/v1/payments/orders", json=test_order_data)
        assert response.status_code == 422

        # Test valid currency
        test_order_data["currency"] = "EUR"
        response = client.post("/api/v1/payments/orders", json=test_order_data)
        assert response.status_code == 200

    def test_payment_method_switching(self, test_order_data):
        """Test creating orders with different payment methods"""
        methods = [PaymentMethod.STRIPE, PaymentMethod.ALIPAY, PaymentMethod.WECHAT]
        for method in methods:
            test_order_data["payment_method"] = method
            response = client.post("/api/v1/payments/orders", json=test_order_data)
            assert response.status_code == 200
            assert response.json()["payment_method"] == method.value

    def test_payment_history_pagination(self, test_order_data, test_user_id):
        """Test payment history pagination"""
        # Create 25 orders
        for _ in range(25):
            client.post("/api/v1/payments/orders", json=test_order_data)

        # Test first page
        response = client.get(f"/api/v1/payments/orders/user/{test_user_id}?skip=0&limit=10")
        assert response.status_code == 200
        assert len(response.json()) == 10

        # Test second page
        response = client.get(f"/api/v1/payments/orders/user/{test_user_id}?skip=10&limit=10")
        assert response.status_code == 200
        assert len(response.json()) == 10

        # Test last page
        response = client.get(f"/api/v1/payments/orders/user/{test_user_id}?skip=20&limit=10")
        assert response.status_code == 200
        assert len(response.json()) == 5
