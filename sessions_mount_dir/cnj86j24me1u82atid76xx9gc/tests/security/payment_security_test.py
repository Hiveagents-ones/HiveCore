import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4
from unittest.mock import patch, MagicMock

from backend.app.main import app
from backend.app.core.database import get_db
from backend.app.crud.payment import PaymentCRUD
from backend.app.schemas.payment import PaymentOrderCreate, PaymentMethod
from backend.app.models.payment import PaymentOrder

client = TestClient(app)


class TestPaymentSecurity:
    """支付模块安全性测试"""

    def setup_method(self):
        """测试前准备"""
        self.test_user_id = uuid4()
        self.test_order_data = {
            "user_id": str(self.test_user_id),
            "amount": 100.00,
            "currency": "CNY",
            "payment_method": PaymentMethod.ALIPAY,
            "description": "Test payment"
        }

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        with patch('backend.app.api.v1.endpoints.payments.get_db') as mock:
            db = MagicMock(spec=Session)
            mock.return_value = db
            yield db

    def test_sql_injection_in_order_creation(self, mock_db):
        """测试订单创建接口防SQL注入"""
        malicious_input = "'; DROP TABLE payment_orders; --"
        order_data = self.test_order_data.copy()
        order_data["description"] = malicious_input

        # 模拟CRUD操作
        mock_crud = MagicMock(spec=PaymentCRUD)
        mock_crud.create_payment_order.return_value = PaymentOrder(
            id=uuid4(),
            user_id=self.test_user_id,
            amount=100.00,
            currency="CNY",
            payment_method=PaymentMethod.ALIPAY,
            description=malicious_input,
            status="pending"
        )
        mock_db.return_value = mock_crud

        response = client.post("/api/v1/payments/orders", json=order_data)
        assert response.status_code == 200
        
        # 验证恶意输入被正确处理，没有执行SQL注入
        assert response.json()["description"] == malicious_input
        mock_crud.create_payment_order.assert_called_once()

    def test_duplicate_order_submission(self, mock_db):
        """测试重复订单提交防护"""
        order_data = self.test_order_data.copy()
        order_data["idempotency_key"] = str(uuid4())

        # 模拟第一次提交成功
        mock_crud = MagicMock(spec=PaymentCRUD)
        mock_crud.create_payment_order.return_value = PaymentOrder(
            id=uuid4(),
            user_id=self.test_user_id,
            amount=100.00,
            currency="CNY",
            payment_method=PaymentMethod.ALIPAY,
            description="Test payment",
            status="pending"
        )
        mock_db.return_value = mock_crud

        # 第一次提交
        response1 = client.post("/api/v1/payments/orders", json=order_data)
        assert response1.status_code == 200

        # 模拟幂等性检查
        mock_crud.get_order_by_idempotency_key.return_value = mock_crud.create_payment_order.return_value

        # 第二次提交相同幂等键
        response2 = client.post("/api/v1/payments/orders", json=order_data)
        assert response2.status_code == 200
        assert response2.json()["id"] == response1.json()["id"]

    def test_invalid_payment_method(self, mock_db):
        """测试无效支付方法"""
        order_data = self.test_order_data.copy()
        order_data["payment_method"] = "INVALID_METHOD"

        response = client.post("/api/v1/payments/orders", json=order_data)
        assert response.status_code == 422

    def test_payment_amount_validation(self, mock_db):
        """测试支付金额验证"""
        # 测试负金额
        order_data = self.test_order_data.copy()
        order_data["amount"] = -100.00

        response = client.post("/api/v1/payments/orders", json=order_data)
        assert response.status_code == 422

        # 测试过大金额
        order_data["amount"] = 999999999.99
        response = client.post("/api/v1/payments/orders", json=order_data)
        assert response.status_code == 422

    def test_webhook_signature_validation(self):
        """测试Webhook签名验证"""
        webhook_data = {
            "order_id": str(uuid4()),
            "status": "success",
            "transaction_id": str(uuid4())
        }

        # 测试无签名
        response = client.post("/api/v1/payments/webhook", json=webhook_data)
        assert response.status_code == 400

        # 测试无效签名
        headers = {"X-Signature": "invalid_signature"}
        response = client.post("/api/v1/payments/webhook", json=webhook_data, headers=headers)
        assert response.status_code == 400

    def test_order_access_control(self, mock_db):
        """测试订单访问控制"""
        other_user_id = uuid4()
        order_id = uuid4()

        # 模拟订单属于其他用户
        mock_crud = MagicMock(spec=PaymentCRUD)
        mock_crud.get_payment_order.return_value = PaymentOrder(
            id=order_id,
            user_id=other_user_id,
            amount=100.00,
            currency="CNY",
            payment_method=PaymentMethod.ALIPAY,
            description="Other user's order",
            status="pending"
        )
        mock_db.return_value = mock_crud

        # 尝试访问其他用户的订单
        response = client.get(f"/api/v1/payments/orders/{order_id}")
        assert response.status_code == 404

    def test_refund_security(self, mock_db):
        """测试退款安全性"""
        order_id = uuid4()
        refund_data = {
            "order_id": str(order_id),
            "amount": 50.00,
            "reason": "Test refund"
        }

        # 模拟订单不存在
        mock_crud = MagicMock(spec=PaymentCRUD)
        mock_crud.get_payment_order.return_value = None
        mock_db.return_value = mock_crud

        response = client.post("/api/v1/payments/refund", json=refund_data)
        assert response.status_code == 404

        # 模拟退款金额超过订单金额
        mock_crud.get_payment_order.return_value = PaymentOrder(
            id=order_id,
            user_id=self.test_user_id,
            amount=30.00,
            currency="CNY",
            payment_method=PaymentMethod.ALIPAY,
            description="Test order",
            status="completed"
        )

        response = client.post("/api/v1/payments/refund", json=refund_data)
        assert response.status_code == 400

    def test_sensitive_data_exposure(self, mock_db):
        """测试敏感数据暴露"""
        order_id = uuid4()

        # 模拟订单包含敏感信息
        mock_crud = MagicMock(spec=PaymentCRUD)
        mock_crud.get_payment_order.return_value = PaymentOrder(
            id=order_id,
            user_id=self.test_user_id,
            amount=100.00,
            currency="CNY",
            payment_method=PaymentMethod.ALIPAY,
            description="Test payment",
            status="pending",
            gateway_transaction_id="sensitive_transaction_id"
        )
        mock_db.return_value = mock_crud

        response = client.get(f"/api/v1/payments/orders/{order_id}")
        assert response.status_code == 200
        
        # 确保敏感信息不在响应中
        assert "gateway_transaction_id" not in response.json()
        assert "sensitive" not in response.json()
