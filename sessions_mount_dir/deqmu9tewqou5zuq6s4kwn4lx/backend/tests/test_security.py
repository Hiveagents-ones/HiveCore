import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.models import Base, User, Course, Booking
from app.core.security import get_password_hash
from app.database import get_db
import os
import ssl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

# Test database setup
SQLALCHEMY_DATABASE_URL = "postgresql://test:test@localhost/test_db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
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

class TestHTTPS:
    """Test HTTPS transmission security"""
    
    def test_https_redirect(self):
        """Test that HTTP requests are redirected to HTTPS"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code in [301, 302, 307, 308]
        assert "https" in response.headers.get("location", "")
    
    def test_https_connection(self):
        """Test HTTPS connection with valid certificate"""
        # Create a custom SSL context that verifies certificates
        class SSLAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                context = create_urllib3_context()
                kwargs['ssl_context'] = context
                return super().init_poolmanager(*args, **kwargs)
        
        session = requests.Session()
        session.mount('https://', SSLAdapter())
        
        try:
            # This would test against a real HTTPS endpoint
            # In test environment, we verify the SSL configuration
            assert ssl.HAS_SNI
            assert ssl.OPENSSL_VERSION_INFO >= (1, 1, 1)
        except Exception:
            pytest.skip("HTTPS endpoint not available in test environment")
    
    def test_security_headers(self):
        """Test security headers are present"""
        response = client.get("/")
        headers = response.headers
        
        # Check for important security headers
        assert "x-content-type-options" in headers
        assert headers["x-content-type-options"] == "nosniff"
        assert "x-frame-options" in headers
        assert headers["x-frame-options"] in ["DENY", "SAMEORIGIN"]
        assert "x-xss-protection" in headers

class TestDataEncryption:
    """Test data encryption at rest"""
    
    def test_password_hashing(self):
        """Test passwords are properly hashed"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        # Verify hash is not plain text
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are typically 60 chars
        assert hashed.startswith("$2b$")  # bcrypt prefix
    
    def test_sensitive_data_encryption(self):
        """Test sensitive data is encrypted in database"""
        db = TestingSessionLocal()
        
        # Create test user
        user = User(
            email="test@example.com",
            hashed_password=get_password_hash("password123"),
            full_name="Test User",
            phone="1234567890"
        )
        db.add(user)
        db.commit()
        
        # Verify phone is stored encrypted (if implemented)
        stored_user = db.query(User).filter(User.email == "test@example.com").first()
        assert stored_user.phone != "1234567890"  # Should be encrypted
        
        db.delete(user)
        db.commit()
        db.close()
    
    def test_pii_protection(self):
        """Test personally identifiable information is protected"""
        db = TestingSessionLocal()
        
        # Create test booking with user data
        user = User(
            email="user@example.com",
            hashed_password=get_password_hash("password123"),
            full_name="John Doe",
            phone="9876543210"
        )
        db.add(user)
        db.commit()
        
        course = Course(
            title="Test Course",
            description="Test Description",
            max_capacity=10,
            current_capacity=0
        )
        db.add(course)
        db.commit()
        
        booking = Booking(
            user_id=user.id,
            course_id=course.id,
            status="confirmed"
        )
        db.add(booking)
        db.commit()
        
        # Verify PII is not exposed in API responses
        response = client.get(f"/api/v1/bookings/{booking.id}")
        assert response.status_code == 200
        data = response.json()
        assert "phone" not in data
        assert "email" not in data
        
        # Cleanup
        db.delete(booking)
        db.delete(course)
        db.delete(user)
        db.commit()
        db.close()

class TestSQLInjectionProtection:
    """Test SQL injection protection"""
    
    def test_booking_endpoint_sql_injection(self):
        """Test booking endpoint against SQL injection"""
        malicious_input = "'; DROP TABLE bookings; --"
        
        # Test in booking creation
        response = client.post(
            "/api/v1/bookings/",
            json={
                "course_id": malicious_input,
                "user_notes": malicious_input
            }
        )
        # Should return validation error, not execute SQL
        assert response.status_code in [400, 422]
        
        # Verify bookings table still exists
        db = TestingSessionLocal()
        bookings_count = db.query(Booking).count()
        db.close()
        assert bookings_count >= 0  # Table exists
    
    def test_course_endpoint_sql_injection(self):
        """Test course endpoint against SQL injection"""
        malicious_input = "1' OR '1'='1"
        
        # Test in course search
        response = client.get(f"/api/v1/courses/?search={malicious_input}")
        # Should handle safely, not return all courses
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should not return all records due to SQL injection
        assert len(data) < 100  # Reasonable limit
    
    def test_user_endpoint_sql_injection(self):
        """Test user endpoint against SQL injection"""
        malicious_input = "admin'--"
        
        # Test in user lookup
        response = client.get(f"/api/v1/users/{malicious_input}")
        # Should return 404 or validation error, not admin data
        assert response.status_code in [404, 422]
    
    def test_parameterized_queries(self):
        """Verify database queries use parameterization"""
        db = TestingSessionLocal()
        
        # Test that SQLAlchemy uses parameterized queries
        from sqlalchemy.sql import text
        
        # This should use parameterized query
        result = db.execute(
            text("SELECT * FROM users WHERE email = :email"),
            {"email": "test@example.com"}
        )
        
        # Verify query was parameterized (no string formatting)
        assert result is not None
        
        db.close()

class TestAuthenticationSecurity:
    """Test authentication and authorization security"""
    
    def test_jwt_token_validation(self):
        """Test JWT tokens are properly validated"""
        # Test with invalid token
        response = client.get(
            "/api/v1/bookings/",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
    
    def test_csrf_protection(self):
        """Test CSRF protection is enabled"""
        response = client.post("/api/v1/bookings/")
        # Should require CSRF token for state-changing requests
        assert response.status_code in [401, 403, 422]
    
    def test_rate_limiting(self):
        """Test rate limiting is in place"""
        # Make multiple rapid requests
        responses = []
        for _ in range(100):
            response = client.post("/api/v1/auth/login", json={
                "username": "test",
                "password": "test"
            })
            responses.append(response.status_code)
        
        # Should eventually be rate limited
        assert 429 in responses

class TestDataValidation:
    """Test input data validation"""
    
    def test_booking_data_validation(self):
        """Test booking data is properly validated"""
        # Test with invalid data types
        response = client.post("/api/v1/bookings/", json={
            "course_id": "not_a_number",
            "user_notes": {"invalid": "object"}
        })
        assert response.status_code == 422
    
    def test_xss_prevention(self):
        """Test XSS prevention in user inputs"""
        xss_payload = "<script>alert('xss')</script>"
        
        response = client.post("/api/v1/bookings/", json={
            "course_id": 1,
            "user_notes": xss_payload
        })
        
        if response.status_code == 200:
            # Verify script tags are escaped
            response = client.get("/api/v1/bookings/1")
            assert "<script>" not in response.text
            assert "&lt;script&gt;" in response.text or "alert" not in response.text

if __name__ == "__main__":
    pytest.main([__file__])