import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.api.deps import get_db
from app.models import Base, User, Member, Payment, PaymentStatus
from app.core.config import settings
from app import crud, schemas
from unittest.mock import patch, MagicMock

from datetime import datetime, timedelta
import stripe
import time

# Test Database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
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

@pytest.fixture(scope="module")
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user(test_db):
    db = TestingSessionLocal()
    user = User(email="test@example.com", hashed_password="hashedpassword", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    db.delete(user)
    db.commit()
    db.close()

@pytest.fixture
def test_member(test_db, test_user):
    db = TestingSessionLocal()
    member = Member(user_id=test_user.id, start_date="2023-01-01", end_date="2023-12-31", is_active=True)
    db.add(member)
    db.commit()
    db.refresh(member)
    yield member
    db.delete(member)
    db.commit()
    db.close()

@pytest.fixture
def auth_headers(test_user):
    return {"Authorization": f"Bearer {test_user.id}"}

# Unit Tests

def test_initiate_payment_success(test_member, auth_headers):
    payment_data = {
        "member_id": test_member.id,
        "amount": 100.0,
        "months": 12
    }
    with patch('stripe.PaymentIntent.create') as mock_intent:
        mock_intent.return_value = MagicMock(id="pi_test", client_secret="secret_test")
        response = client.post("/payments/", json=payment_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["member_id"] == test_member.id
        assert data["amount"] == 100.0
        assert data["status"] == PaymentStatus.PENDING
        assert "client_secret" in data

def test_initiate_payment_member_not_found(auth_headers):
    payment_data = {
        "member_id": 999,
        "amount": 100.0,
        "months": 12
    }
    response = client.post("/payments/", json=payment_data, headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Member not found"

def test_initiate_payment_stripe_error(test_member, auth_headers):
    payment_data = {
        "member_id": test_member.id,
        "amount": 100.0,
        "months": 12
    }
    with patch('stripe.PaymentIntent.create') as mock_intent:
        mock_intent.side_effect = stripe.error.StripeError("Stripe error")
        response = client.post("/payments/", json=payment_data, headers=auth_headers)
        assert response.status_code == 400
        assert "Payment processing error" in response.json()["detail"]

# Integration Tests

def test_payment_flow(test_member, auth_headers):
    payment_data = {
        "member_id": test_member.id,
        "amount": 100.0,
        "months": 12
    }
    with patch('stripe.PaymentIntent.create') as mock_intent:
        mock_intent.return_value = MagicMock(id="pi_test", client_secret="secret_test")
        # Initiate payment
        response = client.post("/payments/", json=payment_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        payment_id = data["id"]
        # Confirm payment
        confirm_data = {
            "payment_intent_id": "pi_test",
            "payment_id": payment_id
        }
        with patch('stripe.PaymentIntent.retrieve') as mock_retrieve:
            mock_retrieve.return_value = MagicMock(status="succeeded")
            response = client.post("/payments/confirm", json=confirm_data, headers=auth_headers)
            assert response.status_code == 200
            assert response.json()["status"] == PaymentStatus.SUCCEEDED

# Security Tests

def test_unauthorized_access():
    payment_data = {
        "member_id": 1,
        "amount": 100.0,
        "months": 12
    }
    response = client.post("/payments/", json=payment_data)
    assert response.status_code == 401

def test_invalid_payment_data(test_member, auth_headers):
    payment_data = {
        "member_id": test_member.id,
        "amount": -100.0,
        "months": 12
    }
    response = client.post("/payments/", json=payment_data, headers=auth_headers)
    assert response.status_code == 422

# Performance Tests

def test_payment_performance(test_member, auth_headers):
    payment_data = {
        "member_id": test_member.id,
        "amount": 100.0,
        "months": 12
    }
    with patch('stripe.PaymentIntent.create') as mock_intent:
        mock_intent.return_value = MagicMock(id="pi_test", client_secret="secret_test")
        start_time = time.time()
        for _ in range(10):
            response = client.post("/payments/", json=payment_data, headers=auth_headers)
            assert response.status_code == 200
        duration = time.time() - start_time
        assert duration < 5.0  # Ensure 10 requests complete within 5 seconds

# Additional Tests for Payment History and Notifications

def test_get_payment_history(test_member, auth_headers):
    # Create a payment first
    payment_data = {
        "member_id": test_member.id,
        "amount": 100.0,
        "months": 12
    }
    with patch('stripe.PaymentIntent.create') as mock_intent:
        mock_intent.return_value = MagicMock(id="pi_test", client_secret="secret_test")
        response = client.post("/payments/", json=payment_data, headers=auth_headers)
        assert response.status_code == 200
    
    # Get payment history
    response = client.get(f"/payments/history/{test_member.id}", headers=auth_headers)
    assert response.status_code == 200
    history = response.json()
    assert len(history) > 0
    assert history[0]["member_id"] == test_member.id
    assert history[0]["amount"] == 100.0

def test_payment_notification_creation(test_member, auth_headers):
    payment_data = {
        "member_id": test_member.id,
        "amount": 100.0,
        "months": 12
    }
    with patch('stripe.PaymentIntent.create') as mock_intent:
        mock_intent.return_value = MagicMock(id="pi_test", client_secret="secret_test")
        response = client.post("/payments/", json=payment_data, headers=auth_headers)
        assert response.status_code == 200
        
        # Check if notification was created
        db = TestingSessionLocal()
        notifications = db.query(models.Notification).filter(
            models.Notification.member_id == test_member.id
        ).all()
        assert len(notifications) > 0
        assert notifications[0].type == models.NotificationType.PAYMENT_SUCCESS
        db.close()

def test_membership_expiry_notification(test_member, auth_headers):
    # Test notification creation for expiring membership
    db = TestingSessionLocal()
    # Update member to expire soon
    test_member.end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    db.commit()
    
    # Trigger notification check
    response = client.post("/notifications/check-expiry", headers=auth_headers)
    assert response.status_code == 200
    
    # Verify notification was created
    notifications = db.query(models.Notification).filter(
        models.Notification.member_id == test_member.id,
        models.Notification.type == models.NotificationType.MEMBERSHIP_EXPIRY
    ).all()
    assert len(notifications) > 0
    db.close()

def test_payment_refund(test_member, auth_headers):
    # Create and confirm a payment first
    payment_data = {
        "member_id": test_member.id,
        "amount": 100.0,
        "months": 12
    }
    with patch('stripe.PaymentIntent.create') as mock_intent:
        mock_intent.return_value = MagicMock(id="pi_test", client_secret="secret_test")
        response = client.post("/payments/", json=payment_data, headers=auth_headers)
        assert response.status_code == 200
        payment_id = response.json()["id"]
    
    # Confirm payment
    confirm_data = {
        "payment_intent_id": "pi_test",
        "payment_id": payment_id
    }
    with patch('stripe.PaymentIntent.retrieve') as mock_retrieve:
        mock_retrieve.return_value = MagicMock(status="succeeded")
        response = client.post("/payments/confirm", json=confirm_data, headers=auth_headers)
        assert response.status_code == 200
    
    # Process refund
    refund_data = {
        "payment_id": payment_id,
        "amount": 50.0
    }
    with patch('stripe.Refund.create') as mock_refund:
        mock_refund.return_value = MagicMock(id="re_test", status="succeeded")
        response = client.post("/payments/refund", json=refund_data, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == PaymentStatus.REFUNDED

def test_payment_webhook_handling(test_member):
    # Test Stripe webhook handling
    webhook_payload = {
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_test",
                "metadata": {
                    "member_id": str(test_member.id),
                    "months": "12"
                },
                "amount": 10000
            }
        }
    }
    
    response = client.post("/payments/webhook", json=webhook_payload)
    assert response.status_code == 200
    
    # Verify payment status updated
    db = TestingSessionLocal()
    payment = db.query(models.Payment).filter(
        models.Payment.stripe_payment_intent_id == "pi_test"
    ).first()
    assert payment.status == PaymentStatus.SUCCEEDED
    db.close()
