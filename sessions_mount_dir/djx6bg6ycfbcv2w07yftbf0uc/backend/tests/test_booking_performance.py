import pytest
import asyncio
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ..app.main import app
from ..app.models import Base, Booking, Course, User
from ..app.core.security import create_access_token
from ..app.dependencies import get_db

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
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password"
    )
    db = TestingSessionLocal()
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(data={"sub": user.username})
    db.close()
    return {"user": user, "token": token}

@pytest.fixture(scope="module")
def test_courses():
    courses = []
    db = TestingSessionLocal()
    for i in range(5):
        course = Course(
            title=f"Test Course {i}",
            description=f"Description for course {i}",
            price=100.0 + i * 10,
            duration=60,
            max_participants=10
        )
        db.add(course)
        courses.append(course)
    db.commit()
    for course in courses:
        db.refresh(course)
    db.close()
    return courses

@pytest.mark.performance
def test_concurrent_booking_creation(test_user, test_courses):
    """Test performance of concurrent booking creation"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    booking_time = (datetime.utcnow() + timedelta(days=1)).isoformat()
    
    async def create_booking(course_id):
        response = client.post(
            "/bookings/",
            params={"course_id": course_id, "booking_time": booking_time},
            headers=headers
        )
        return response
    
    async def run_concurrent_requests():
        tasks = [create_booking(course.id) for course in test_courses]
        return await asyncio.gather(*tasks)
    
    # Run concurrent requests
    responses = asyncio.run(run_concurrent_requests())
    
    # Verify all requests succeeded
    for response in responses:
        assert response.status_code == 200
        assert "booking_id" in response.json()
    
    # Verify bookings were created
    db = TestingSessionLocal()
    bookings = db.query(Booking).filter(Booking.user_id == test_user['user'].id).all()
    assert len(bookings) == len(test_courses)
    db.close()

@pytest.mark.performance
def test_booking_creation_performance(test_user, test_courses):
    """Test performance of single booking creation"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    booking_time = (datetime.utcnow() + timedelta(days=2)).isoformat()
    
    # Measure response time
    start_time = datetime.utcnow()
    response = client.post(
        "/bookings/",
        params={"course_id": test_courses[0].id, "booking_time": booking_time},
        headers=headers
    )
    end_time = datetime.utcnow()
    
    # Verify response
    assert response.status_code == 200
    assert "booking_id" in response.json()
    
    # Verify performance (response time should be under 500ms)
    response_time = (end_time - start_time).total_seconds() * 1000
    assert response_time < 500, f"Response time {response_time}ms exceeded threshold"

@pytest.mark.performance
def test_booking_retrieval_performance(test_user):
    """Test performance of booking retrieval"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    # Measure response time for getting all bookings
    start_time = datetime.utcnow()
    response = client.get("/bookings/", headers=headers)
    end_time = datetime.utcnow()
    
    # Verify response
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    
    # Verify performance (response time should be under 300ms)
    response_time = (end_time - start_time).total_seconds() * 1000
    assert response_time < 300, f"Response time {response_time}ms exceeded threshold"

@pytest.mark.performance
def test_booking_cancellation_performance(test_user):
    """Test performance of booking cancellation"""
    headers = {"Authorization": f"Bearer {test_user['token']}"}
    
    # Create a booking first
    booking_time = (datetime.utcnow() + timedelta(days=3)).isoformat()
    create_response = client.post(
        "/bookings/",
        params={"course_id": 1, "booking_time": booking_time},
        headers=headers
    )
    booking_id = create_response.json()["booking_id"]
    
    # Measure response time for cancellation
    start_time = datetime.utcnow()
    response = client.delete(f"/bookings/{booking_id}", headers=headers)
    end_time = datetime.utcnow()
    
    # Verify response
    assert response.status_code == 200
    
    # Verify performance (response time should be under 400ms)
    response_time = (end_time - start_time).total_seconds() * 1000
    assert response_time < 400, f"Response time {response_time}ms exceeded threshold"

@pytest.mark.performance
def test_multiple_user_booking_performance():
    """Test performance with multiple users creating bookings"""
    # Create multiple test users
    users = []
    db = TestingSessionLocal()
    for i in range(10):
        user = User(
            username=f"user{i}",
            email=f"user{i}@example.com",
            hashed_password="hashed_password"
        )
        db.add(user)
        users.append(user)
    db.commit()
    for user in users:
        db.refresh(user)
    db.close()
    
    # Create bookings for each user
    async def create_booking_for_user(user):
        token = create_access_token(data={"sub": user.username})
        headers = {"Authorization": f"Bearer {token}"}
        booking_time = (datetime.utcnow() + timedelta(days=4)).isoformat()
        response = client.post(
            "/bookings/",
            params={"course_id": 1, "booking_time": booking_time},
            headers=headers
        )
        return response
    
    async def run_concurrent_bookings():
        tasks = [create_booking_for_user(user) for user in users]
        return await asyncio.gather(*tasks)
    
    # Run concurrent requests
    responses = asyncio.run(run_concurrent_bookings())
    
    # Verify all requests succeeded
    for response in responses:
        assert response.status_code == 200
        assert "booking_id" in response.json()
    
    # Verify total bookings
    db = TestingSessionLocal()
    total_bookings = db.query(Booking).filter(Booking.course_id == 1).count()
    assert total_bookings >= len(users)
    db.close()
