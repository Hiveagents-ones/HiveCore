import pytest
import asyncio
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.dependencies import get_db
from app.models import Base, Merchant, User, Course, Booking, Payment
from app.core.config import settings

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
def test_data():
    db = TestingSessionLocal()
    
    # Create test merchant
    merchant = Merchant(
        name="Test Merchant",
        email="merchant@test.com",
        phone="1234567890",
        is_active=True
    )
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    
    # Create test courses
    courses = []
    for i in range(5):
        course = Course(
            name=f"Test Course {i}",
            description=f"Description for course {i}",
            merchant_id=merchant.id,
            price=100.0 * (i + 1),
            duration=60,
            max_capacity=10,
            is_active=True
        )
        db.add(course)
        courses.append(course)
    db.commit()
    
    # Create test bookings
    for i in range(100):
        booking = Booking(
            course_id=courses[i % 5].id,
            merchant_id=merchant.id,
            user_email=f"user{i}@test.com",
            user_name=f"User {i}",
            booking_time=datetime.now() - timedelta(days=i),
            status="confirmed"
        )
        db.add(booking)
    
    # Create test payments
    for i in range(50):
        payment = Payment(
            booking_id=i + 1,
            amount=100.0,
            payment_time=datetime.now() - timedelta(days=i),
            status="completed"
        )
        db.add(payment)
    
    db.commit()
    
    yield {
        "merchant_id": merchant.id,
        "course_ids": [c.id for c in courses]
    }
    
    # Cleanup
    db.query(Payment).delete()
    db.query(Booking).delete()
    db.query(Course).delete()
    db.query(Merchant).delete()
    db.commit()
    db.close()


class TestAnalyticsPerformance:
    """Performance tests for analytics endpoints"""
    
    def test_analytics_response_time(self, test_data):
        """Test that analytics endpoint responds within acceptable time"""
        start_date = (datetime.now() - timedelta(days=30)).isoformat()
        end_date = datetime.now().isoformat()
        
        payload = {
            "start_date": start_date,
            "end_date": end_date,
            "course_ids": test_data["course_ids"],
            "include_growth": True,
            "include_revenue": True
        }
        
        # Measure response time
        start_time = datetime.now()
        response = client.post(
            "/analytics/",
            json=payload,
            headers={"X-Merchant-ID": str(test_data["merchant_id"])}
        )
        end_time = datetime.now()
        
        response_time = (end_time - start_time).total_seconds()
        
        assert response.status_code == 200
        assert response_time < 2.0  # Should respond within 2 seconds
        assert response.json()["success"] is True
    
    def test_analytics_large_date_range(self, test_data):
        """Test performance with maximum allowed date range (1 year)"""
        start_date = (datetime.now() - timedelta(days=365)).isoformat()
        end_date = datetime.now().isoformat()
        
        payload = {
            "start_date": start_date,
            "end_date": end_date,
            "course_ids": test_data["course_ids"],
            "include_growth": True,
            "include_revenue": True
        }
        
        start_time = datetime.now()
        response = client.post(
            "/analytics/",
            json=payload,
            headers={"X-Merchant-ID": str(test_data["merchant_id"])}
        )
        end_time = datetime.now()
        
        response_time = (end_time - start_time).total_seconds()
        
        assert response.status_code == 200
        assert response_time < 5.0  # Should handle large date ranges within 5 seconds
    
    def test_analytics_concurrent_requests(self, test_data):
        """Test performance under concurrent requests"""
        import threading
        import time
        
        start_date = (datetime.now() - timedelta(days=30)).isoformat()
        end_date = datetime.now().isoformat()
        
        payload = {
            "start_date": start_date,
            "end_date": end_date,
            "course_ids": test_data["course_ids"],
            "include_growth": True,
            "include_revenue": True
        }
        
        results = []
        
        def make_request():
            start = time.time()
            response = client.post(
                "/analytics/",
                json=payload,
                headers={"X-Merchant-ID": str(test_data["merchant_id"])}
            )
            end = time.time()
            results.append({
                "status_code": response.status_code,
                "response_time": end - start
            })
        
        # Create 10 concurrent threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all requests succeeded
        assert len(results) == 10
        for result in results:
            assert result["status_code"] == 200
            assert result["response_time"] < 3.0  # Each request should complete within 3 seconds
    
    def test_analytics_caching_performance(self, test_data):
        """Test that caching improves response time for repeated requests"""
        start_date = (datetime.now() - timedelta(days=30)).isoformat()
        end_date = datetime.now().isoformat()
        
        payload = {
            "start_date": start_date,
            "end_date": end_date,
            "course_ids": test_data["course_ids"],
            "include_growth": True,
            "include_revenue": True
        }
        
        # First request (cache miss)
        start_time = datetime.now()
        response1 = client.post(
            "/analytics/",
            json=payload,
            headers={"X-Merchant-ID": str(test_data["merchant_id"])}
        )
        first_response_time = (datetime.now() - start_time).total_seconds()
        
        # Second request (cache hit)
        start_time = datetime.now()
        response2 = client.post(
            "/analytics/",
            json=payload,
            headers={"X-Merchant-ID": str(test_data["merchant_id"])}
        )
        second_response_time = (datetime.now() - start_time).total_seconds()
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert second_response_time < first_response_time  # Cached response should be faster
        assert second_response_time < 0.5  # Cached response should be very fast
    
    def test_analytics_memory_usage(self, test_data):
        """Test that analytics endpoint doesn't consume excessive memory"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        start_date = (datetime.now() - timedelta(days=30)).isoformat()
        end_date = datetime.now().isoformat()
        
        payload = {
            "start_date": start_date,
            "end_date": end_date,
            "course_ids": test_data["course_ids"],
            "include_growth": True,
            "include_revenue": True
        }
        
        # Make multiple requests
        for _ in range(20):
            response = client.post(
                "/analytics/",
                json=payload,
                headers={"X-Merchant-ID": str(test_data["merchant_id"])}
            )
            assert response.status_code == 200
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal (< 50MB)
        assert memory_increase < 50
    
    def test_analytics_data_integrity(self, test_data):
        """Verify analytics data integrity under performance load"""
        start_date = (datetime.now() - timedelta(days=30)).isoformat()
        end_date = datetime.now().isoformat()
        
        payload = {
            "start_date": start_date,
            "end_date": end_date,
            "course_ids": test_data["course_ids"],
            "include_growth": True,
            "include_revenue": True
        }
        
        response = client.post(
            "/analytics/",
            json=payload,
            headers={"X-Merchant-ID": str(test_data["merchant_id"])}
        )
        
        assert response.status_code == 200
        data = response.json()["data"]
        
        # Verify data structure
        assert "overview" in data
        assert "booking_stats" in data
        assert "member_growth" in data
        assert "popular_courses" in data
        assert "revenue_stats" in data
        
        # Verify data consistency
        assert data["overview"]["total_bookings"] == 100
        assert len(data["popular_courses"]) <= 5
        assert len(data["revenue_stats"]) > 0
        
        # Verify no data corruption
        for stat in data["booking_stats"]:
            assert "date" in stat
            assert "count" in stat
            assert isinstance(stat["count"], int)
            assert stat["count"] >= 0
