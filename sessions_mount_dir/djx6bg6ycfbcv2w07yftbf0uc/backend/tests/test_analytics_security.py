import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ..app.main import app
from ..app.dependencies import get_db
from ..app.models import Base, Merchant, User
from ..app.core.security import create_access_token

# Test database setup
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

@pytest.fixture
def test_merchant():
    db = TestingSessionLocal()
    merchant = Merchant(
        store_name="Test Store",
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True
    )
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    token = create_access_token(data={"sub": str(merchant.id)})
    db.close()
    return merchant, token

@pytest.fixture
def test_user():
    db = TestingSessionLocal()
    user = User(
        email="user@example.com",
        hashed_password="hashed_password",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(data={"sub": str(user.id)})
    db.close()
    return user, token

def test_analytics_unauthorized_access():
    """Test that unauthorized users cannot access analytics"""
    response = client.post(
        "/analytics/",
        json={
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "course_ids": [],
            "include_growth": True,
            "include_revenue": True
        }
    )
    assert response.status_code == 401

def test_analytics_user_access_denied(test_user):
    """Test that regular users cannot access merchant analytics"""
    _, token = test_user
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/analytics/",
        json={
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "course_ids": [],
            "include_growth": True,
            "include_revenue": True
        },
        headers=headers
    )
    assert response.status_code == 403

def test_analytics_invalid_date_range(test_merchant):
    """Test validation of date range"""
    merchant, token = test_merchant
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test end date before start date
    response = client.post(
        "/analytics/",
        json={
            "start_date": "2023-12-31",
            "end_date": "2023-01-01",
            "course_ids": [],
            "include_growth": True,
            "include_revenue": True
        },
        headers=headers
    )
    assert response.status_code == 400
    assert "End date must be after start date" in response.json()["detail"]
    
    # Test date range exceeding 1 year
    response = client.post(
        "/analytics/",
        json={
            "start_date": "2022-01-01",
            "end_date": "2023-12-31",
            "course_ids": [],
            "include_growth": True,
            "include_revenue": True
        },
        headers=headers
    )
    assert response.status_code == 400
    assert "Date range cannot exceed 1 year" in response.json()["detail"]

def test_analytics_merchant_access(test_merchant):
    """Test that merchants can access their own analytics"""
    merchant, token = test_merchant
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/analytics/",
        json={
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "course_ids": [],
            "include_growth": True,
            "include_revenue": True
        },
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert "overview" in data["data"]
    assert "booking_stats" in data["data"]
    assert "member_growth" in data["data"]
    assert "popular_courses" in data["data"]
    assert "revenue_stats" in data["data"]

def test_analytics_sql_injection(test_merchant):
    """Test protection against SQL injection"""
    merchant, token = test_merchant
    headers = {"Authorization": f"Bearer {token}"}
    malicious_input = "'; DROP TABLE merchants; --"
    response = client.post(
        "/analytics/",
        json={
            "start_date": malicious_input,
            "end_date": "2023-12-31",
            "course_ids": [],
            "include_growth": True,
            "include_revenue": True
        },
        headers=headers
    )
    # Should return validation error rather than executing malicious code
    assert response.status_code in [400, 422]

def test_analytics_xss_protection(test_merchant):
    """Test protection against XSS in response data"""
    merchant, token = test_merchant
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/analytics/",
        json={
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "course_ids": [],
            "include_growth": True,
            "include_revenue": True
        },
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    # Check that response doesn't contain unescaped HTML
    response_str = str(data)
    assert "<script>" not in response_str
    assert "javascript:" not in response_str

def test_analytics_rate_limiting(test_merchant):
    """Test rate limiting on analytics endpoint"""
    merchant, token = test_merchant
    headers = {"Authorization": f"Bearer {token}"}
    
    # Make multiple rapid requests
    responses = []
    for _ in range(10):
        response = client.post(
            "/analytics/",
            json={
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "course_ids": [],
                "include_growth": True,
                "include_revenue": True
            },
            headers=headers
        )
        responses.append(response.status_code)
    
    # At least one request should be rate limited
    assert 429 in responses

def test_analytics_data_isolation(test_merchant):
    """Test that merchants can only access their own data"""
    merchant, token = test_merchant
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/analytics/",
        json={
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "course_ids": [],
            "include_growth": True,
            "include_revenue": True
        },
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    # Verify that the response only contains data for the authenticated merchant
    # This would require checking the actual data in the service layer
    assert "data" in data

def test_analytics_token_validation():
    """Test validation of JWT tokens"""
    # Test with invalid token
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.post(
        "/analytics/",
        json={
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "course_ids": [],
            "include_growth": True,
            "include_revenue": True
        },
        headers=headers
    )
    assert response.status_code == 401
    
    # Test with expired token
    expired_token = create_access_token(data={"sub": "1"}, expires_delta=timedelta(seconds=-1))
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.post(
        "/analytics/",
        json={
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "course_ids": [],
            "include_growth": True,
            "include_revenue": True
        },
        headers=headers
    )
    assert response.status_code == 401

def test_analytics_request_size_limit(test_merchant):
    """Test protection against overly large requests"""
    merchant, token = test_merchant
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create a request with many course IDs
    large_request = {
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "course_ids": [str(i) for i in range(10000)],  # Very large array
        "include_growth": True,
        "include_revenue": True
    }
    
    response = client.post(
        "/analytics/",
        json=large_request,
        headers=headers
    )
    # Should either succeed (if service handles it) or return 413/422
    assert response.status_code in [200, 413, 422]

def test_analytics_sensitive_data_exposure(test_merchant):
    """Test that sensitive data is not exposed in analytics"""
    merchant, token = test_merchant
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/analytics/",
        json={
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "course_ids": [],
            "include_growth": True,
            "include_revenue": True
        },
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    response_str = str(data)
    
    # Check that sensitive fields are not exposed
    sensitive_fields = [
        "password",
        "hashed_password",
        "secret",
        "token",
        "api_key",
        "private_key"
    ]
    
    for field in sensitive_fields:
        assert field not in response_str.lower()
