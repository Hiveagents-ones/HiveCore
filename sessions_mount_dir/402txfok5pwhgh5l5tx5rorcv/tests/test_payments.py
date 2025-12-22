import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.main import app
from backend.app.database import get_db, Base
from backend.app import models, schemas

# 创建测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建测试表
Base.metadata.create_all(bind=engine)

# 覆盖数据库依赖
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture
def test_member():
    """创建测试会员"""
    member_data = {
        "name": "Test Member",
        "contact": "test@example.com",
        "level": "regular",
        "status": "active"
    }
    response = client.post("/api/v1/members", json=member_data)
    return response.json()

@pytest.fixture
def test_payment_data(test_member):
    """测试支付数据"""
    return {
        "member_id": test_member["id"],
        "amount": 100.00,
        "type": "membership",
        "description": "Monthly membership fee"
    }

def test_create_payment(test_payment_data):
    """测试创建支付"""
    response = client.post("/api/v1/payments", json=test_payment_data)
    assert response.status_code == 200
    data = response.json()
    assert data["member_id"] == test_payment_data["member_id"]
    assert data["amount"] == test_payment_data["amount"]
    assert data["type"] == test_payment_data["type"]
    assert data["status"] == schemas.PaymentStatus.PENDING

def test_create_payment_invalid_member():
    """测试创建支付时会员不存在"""
    invalid_payment = {
        "member_id": 99999,
        "amount": 100.00,
        "type": "membership",
        "description": "Test payment"
    }
    response = client.post("/api/v1/payments", json=invalid_payment)
    assert response.status_code == 404
    assert "Member not found" in response.json()["detail"]

def test_payment_callback_success(test_payment_data):
    """测试支付回调成功"""
    # 先创建支付
    create_response = client.post("/api/v1/payments", json=test_payment_data)
    payment = create_response.json()
    
    # 模拟回调数据
    callback_data = {
        "payment_id": payment["id"],
        "status": schemas.PaymentStatus.SUCCESS,
        "transaction_id": "test_tx_12345"
    }
    
    response = client.post("/api/v1/payments/callback/alipay", json=callback_data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # 验证支付状态已更新
    get_response = client.get(f"/api/v1/payments?member_id={test_payment_data['member_id']}")
    payments = get_response.json()
    assert len(payments) > 0
    assert payments[0]["status"] == schemas.PaymentStatus.SUCCESS

def test_payment_callback_invalid_payment():
    """测试支付回调时支付不存在"""
    callback_data = {
        "payment_id": 99999,
        "status": schemas.PaymentStatus.SUCCESS,
        "transaction_id": "test_tx_12345"
    }
    
    response = client.post("/api/v1/payments/callback/alipay", json=callback_data)
    assert response.status_code == 404
    assert "Payment not found" in response.json()["detail"]

def test_list_payments(test_member, test_payment_data):
    """测试获取支付列表"""
    # 创建多个支付
    for i in range(3):
        payment_data = test_payment_data.copy()
        payment_data["amount"] = 100.00 + i * 10
        client.post("/api/v1/payments", json=payment_data)
    
    # 获取支付列表
    response = client.get(f"/api/v1/payments?member_id={test_member['id']}")
    assert response.status_code == 200
    payments = response.json()
    assert len(payments) >= 3
    
    # 验证返回的支付都属于该会员
    for payment in payments:
        assert payment["member_id"] == test_member["id"]

def test_list_payments_empty():
    """测试获取空支付列表"""
    response = client.get("/api/v1/payments?member_id=99999")
    assert response.status_code == 200
    assert response.json() == []

def test_payment_types():
    """测试不同类型的支付"""
    member_response = client.post("/api/v1/members", json={
        "name": "Test Member 2",
        "contact": "test2@example.com",
        "level": "regular",
        "status": "active"
    })
    member = member_response.json()
    
    payment_types = ["membership", "personal_training", "course_booking"]
    
    for payment_type in payment_types:
        payment_data = {
            "member_id": member["id"],
            "amount": 100.00,
            "type": payment_type,
            "description": f"Test {payment_type} payment"
        }
        response = client.post("/api/v1/payments", json=payment_data)
        assert response.status_code == 200
        assert response.json()["type"] == payment_type

def test_payment_amount_validation(test_member):
    """测试支付金额验证"""
    # 测试负金额
    invalid_payment = {
        "member_id": test_member["id"],
        "amount": -100.00,
        "type": "membership",
        "description": "Invalid payment"
    }
    response = client.post("/api/v1/payments", json=invalid_payment)
    assert response.status_code == 422  # Validation error
    
    # 测试零金额
    invalid_payment["amount"] = 0
    response = client.post("/api/v1/payments", json=invalid_payment)
    assert response.status_code == 422  # Validation error

def test_payment_status_flow(test_payment_data):
    """测试支付状态流转"""
    # 创建支付
    create_response = client.post("/api/v1/payments", json=test_payment_data)
    payment = create_response.json()
    assert payment["status"] == schemas.PaymentStatus.PENDING
    
    # 模拟支付成功
    callback_data = {
        "payment_id": payment["id"],
        "status": schemas.PaymentStatus.SUCCESS,
        "transaction_id": "test_tx_12345"
    }
    response = client.post("/api/v1/payments/callback/alipay", json=callback_data)
    assert response.status_code == 200
    
    # 验证状态已更新
    get_response = client.get(f"/api/v1/payments?member_id={test_payment_data['member_id']}")
    updated_payment = get_response.json()[0]
    assert updated_payment["status"] == schemas.PaymentStatus.SUCCESS
    assert updated_payment["transaction_id"] == "test_tx_12345"

# 清理测试数据
def teardown_module():
    Base.metadata.drop_all(bind=engine)
