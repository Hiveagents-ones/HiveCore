import asyncio
import time
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.models import Course, Booking, User
from app.core.database import get_db
from app.core.security import create_access_token

async def test_booking_response_time():
    """Test booking operation response time"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create test user
        user_data = {"email": "test@example.com", "password": "testpass123"}
        await client.post("/api/v1/auth/register", json=user_data)
        
        # Login and get token
        login_data = {"username": "test@example.com", "password": "testpass123"}
        response = await client.post("/api/v1/auth/login", data=login_data)
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create test course
        course_data = {
            "name": "Test Yoga Class",
            "description": "Performance test class",
            "capacity": 20,
            "start_time": "2024-01-01T10:00:00",
            "end_time": "2024-01-01T11:00:00"
        }
        response = await client.post("/api/v1/courses", json=course_data, headers=headers)
        course_id = response.json()["id"]
        
        # Measure booking response time
        start_time = time.time()
        response = await client.post(f"/api/v1/bookings/{course_id}", headers=headers)
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response.status_code == 201
        assert response_time < 0.5  # Should respond within 500ms
        
        print(f"Booking response time: {response_time:.3f}s")

async def test_concurrent_bookings():
    """Test system stability under high concurrent bookings"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create test user
        user_data = {"email": "concurrent@example.com", "password": "testpass123"}
        await client.post("/api/v1/auth/register", json=user_data)
        
        # Login and get token
        login_data = {"username": "concurrent@example.com", "password": "testpass123"}
        response = await client.post("/api/v1/auth/login", data=login_data)
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create test course with limited capacity
        course_data = {
            "name": "Concurrent Test Class",
            "description": "High concurrency test class",
            "capacity": 10,
            "start_time": "2024-01-01T10:00:00",
            "end_time": "2024-01-01T11:00:00"
        }
        response = await client.post("/api/v1/courses", json=course_data, headers=headers)
        course_id = response.json()["id"]
        
        # Create multiple users for concurrent booking
        users = []
        for i in range(15):  # More users than capacity
            user_data = {"email": f"user{i}@example.com", "password": "testpass123"}
            await client.post("/api/v1/auth/register", json=user_data)
            login_data = {"username": f"user{i}@example.com", "password": "testpass123"}
            response = await client.post("/api/v1/auth/login", data=login_data)
            users.append({"token": response.json()["access_token"], "id": i})
        
        # Concurrent booking attempts
        async def book_course(user):
            headers = {"Authorization": f"Bearer {user['token']}"}
            start_time = time.time()
            response = await client.post(f"/api/v1/bookings/{course_id}", headers=headers)
            end_time = time.time()
            return {
                "user_id": user["id"],
                "status": response.status_code,
                "response_time": end_time - start_time
            }
        
        # Execute concurrent bookings
        tasks = [book_course(user) for user in users]
        results = await asyncio.gather(*tasks)
        
        # Analyze results
        successful_bookings = [r for r in results if r["status"] == 201]
        failed_bookings = [r for r in results if r["status"] == 400]
        
        # Verify capacity constraints
        assert len(successful_bookings) == 10  # Should match course capacity
        assert len(failed_bookings) == 5  # Remaining users should fail
        
        # Verify response times
        avg_response_time = sum(r["response_time"] for r in results) / len(results)
        max_response_time = max(r["response_time"] for r in results)
        
        assert avg_response_time < 1.0  # Average should be under 1 second
        assert max_response_time < 2.0  # Max should be under 2 seconds
        
        print(f"Concurrent bookings test passed:")
        print(f"  Successful bookings: {len(successful_bookings)}")
        print(f"  Failed bookings: {len(failed_bookings)}")
        print(f"  Average response time: {avg_response_time:.3f}s")
        print(f"  Max response time: {max_response_time:.3f}s")

async def test_course_list_performance():
    """Test course list endpoint performance"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create test user
        user_data = {"email": "list@example.com", "password": "testpass123"}
        await client.post("/api/v1/auth/register", json=user_data)
        
        # Login and get token
        login_data = {"username": "list@example.com", "password": "testpass123"}
        response = await client.post("/api/v1/auth/login", data=login_data)
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create multiple courses
        for i in range(50):
            course_data = {
                "name": f"Course {i}",
                "description": f"Description for course {i}",
                "capacity": 20,
                "start_time": f"2024-01-{i+1:02d}T10:00:00",
                "end_time": f"2024-01-{i+1:02d}T11:00:00"
            }
            await client.post("/api/v1/courses", json=course_data, headers=headers)
        
        # Test list performance
        start_time = time.time()
        response = await client.get("/api/v1/courses", headers=headers)
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response.status_code == 200
        assert len(response.json()) == 50
        assert response_time < 0.3  # Should respond within 300ms
        
        print(f"Course list response time: {response_time:.3f}s")

async def test_my_bookings_performance():
    """Test my bookings endpoint performance"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create test user
        user_data = {"email": "mybookings@example.com", "password": "testpass123"}
        await client.post("/api/v1/auth/register", json=user_data)
        
        # Login and get token
        login_data = {"username": "mybookings@example.com", "password": "testpass123"}
        response = await client.post("/api/v1/auth/login", data=login_data)
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create courses and book them
        course_ids = []
        for i in range(20):
            course_data = {
                "name": f"My Course {i}",
                "description": f"Description {i}",
                "capacity": 20,
                "start_time": f"2024-01-{i+1:02d}T10:00:00",
                "end_time": f"2024-01-{i+1:02d}T11:00:00"
            }
            response = await client.post("/api/v1/courses", json=course_data, headers=headers)
            course_ids.append(response.json()["id"])
            await client.post(f"/api/v1/bookings/{response.json()['id']}", headers=headers)
        
        # Test my bookings performance
        start_time = time.time()
        response = await client.get("/api/v1/bookings/my", headers=headers)
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response.status_code == 200
        assert len(response.json()) == 20
        assert response_time < 0.3  # Should respond within 300ms
        
        print(f"My bookings response time: {response_time:.3f}s")

if __name__ == "__main__":
    asyncio.run(test_booking_response_time())
    asyncio.run(test_concurrent_bookings())
    asyncio.run(test_course_list_performance())
    asyncio.run(test_my_bookings_performance())
    print("All performance tests passed!")