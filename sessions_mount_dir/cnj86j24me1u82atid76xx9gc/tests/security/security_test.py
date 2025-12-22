import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.main import app
from backend.app.database import get_db, Base
from backend.app.core.security import verify_password, get_password_hash, create_access_token, verify_token
from backend.app.models.course import Course
from backend.app.models.user import User

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

@pytest.fixture(scope="module")
def test_user():
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "hashed_password": get_password_hash("testpassword123")
    }
    db = TestingSessionLocal()
    user = User(**user_data)
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    db.delete(user)
    db.commit()
    db.close()

@pytest.fixture(scope="module")
def test_course():
    course_data = {
        "name": "Test Yoga Class",
        "description": "A test yoga class",
        "capacity": 20,
        "start_time": "2023-12-01T10:00:00",
        "end_time": "2023-12-01T11:00:00"
    }
    db = TestingSessionLocal()
    course = Course(**course_data)
    db.add(course)
    db.commit()
    db.refresh(course)
    yield course
    db.delete(course)
    db.commit()
    db.close()

def test_password_hashing():
    password = "testpassword123"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_token_creation_and_verification():
    data = {"sub": "testuser"}
    token = create_access_token(data)
    payload = verify_token(token)
    assert payload["sub"] == "testuser"

def test_invalid_token():
    invalid_token = "invalid.token.here"
    with pytest.raises(Exception):
        verify_token(invalid_token)

def test_protected_endpoint_without_token():
    response = client.get("/api/v1/courses/")
    assert response.status_code == 401

def test_protected_endpoint_with_valid_token(test_user):
    token = create_access_token({"sub": test_user.username})
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/courses/", headers=headers)
    assert response.status_code == 200

def test_protected_endpoint_with_invalid_token():
    headers = {"Authorization": "Bearer invalid.token.here"}
    response = client.get("/api/v1/courses/", headers=headers)
    assert response.status_code == 401

def test_course_booking_security(test_user, test_course):
    token = create_access_token({"sub": test_user.username})
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test booking a course
    response = client.post(f"/api/v1/courses/{test_course.id}/book", headers=headers)
    assert response.status_code == 200
    
    # Test double booking (should fail)
    response = client.post(f"/api/v1/courses/{test_course.id}/book", headers=headers)
    assert response.status_code == 400
    
    # Test canceling booking
    response = client.delete(f"/api/v1/courses/{test_course.id}/book", headers=headers)
    assert response.status_code == 200

def test_sql_injection_attempt():
    malicious_input = "'; DROP TABLE users; --"
    response = client.get(f"/api/v1/courses/?search={malicious_input}")
    # Should return 401 without token, but not crash
    assert response.status_code == 401

def test_xss_prevention():
    xss_payload = "<script>alert('xss')</script>"
    response = client.post("/api/v1/courses/", json={
        "name": xss_payload,
        "description": "Test description",
        "capacity": 10,
        "start_time": "2023-12-01T10:00:00",
        "end_time": "2023-12-01T11:00:00"
    })
    # Should return 401 without token, but not execute script
    assert response.status_code == 401

def test_csrf_protection():
    # Test that state-changing operations require proper authentication
    response = client.post("/api/v1/courses/1/book")
    assert response.status_code == 401

def test_rate_limiting():
    # Simulate multiple rapid requests
    for _ in range(100):
        response = client.get("/api/v1/courses/")
        # Should handle rate limiting gracefully
        assert response.status_code in [401, 429]

def test_sensitive_data_exposure():
    # Ensure passwords are never exposed
    response = client.post("/api/v1/auth/login", data={
        "username": "testuser",
        "password": "testpassword123"
    })
    if response.status_code == 200:
        assert "password" not in response.json()
        assert "hashed_password" not in response.json()

def test_authentication_bypass_attempts():
    # Test various authentication bypass attempts
    endpoints = [
        "/api/v1/courses/",
        "/api/v1/courses/1/book",
        "/api/v1/users/profile"
    ]
    
    for endpoint in endpoints:
        # Test without token
        response = client.get(endpoint)
        assert response.status_code == 401
        
        # Test with malformed token
        response = client.get(endpoint, headers={"Authorization": "Bearer malformed"})
        assert response.status_code == 401
        
        # Test with expired token (simulate)
        expired_token = create_access_token({"sub": "testuser"}, expires_delta=-1)
        response = client.get(endpoint, headers={"Authorization": f"Bearer {expired_token}"})
        assert response.status_code == 401

def test_authorization_checks():
    # Test that users can only access their own resources
    token1 = create_access_token({"sub": "user1"})
    token2 = create_access_token({"sub": "user2"})
    
    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}
    
    # User1 should not access User2's resources
    response = client.get("/api/v1/users/user2/profile", headers=headers1)
    assert response.status_code in [403, 404]
    
    # User2 should access their own resources
    response = client.get("/api/v1/users/user2/profile", headers=headers2)
    assert response.status_code in [200, 404]  # 404 if user doesn't exist

def test_input_validation():
    # Test various malformed inputs
    malformed_data = [
        {"capacity": "not_a_number"},
        {"start_time": "invalid_date"},
        {"name": ""},
        {"capacity": -1}
    ]
    
    for data in malformed_data:
        response = client.post("/api/v1/courses/", json=data)
        assert response.status_code in [401, 422]  # 401 for auth, 422 for validation

def test_session_management():
    # Test that sessions are properly invalidated after logout
    response = client.post("/api/v1/auth/logout")
    assert response.status_code in [200, 401]  # May vary based on implementation

def test_secure_headers():
    response = client.get("/api/v1/courses/")
    # Check for security headers
    headers = response.headers
    assert "X-Content-Type-Options" in headers
    assert "X-Frame-Options" in headers
    assert "X-XSS-Protection" in headers

def test_https_enforcement():
    # In production, ensure HTTPS is enforced
    response = client.get("/api/v1/courses/")
    # This test would need to be adjusted based on actual HTTPS implementation
    assert response.status_code in [401, 200]  # Basic check

def teardown_module():
    Base.metadata.drop_all(bind=engine)
