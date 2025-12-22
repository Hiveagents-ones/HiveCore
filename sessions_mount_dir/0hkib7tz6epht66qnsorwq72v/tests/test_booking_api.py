import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db, Base
from app.models.booking import Booking as BookingModel, BookingStatus
from app.schemas.booking import BookingCreate, BookingUpdate

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


class TestBookingAPI:
    """Test suite for Booking API endpoints"""

    def setup_method(self):
        """Setup test data before each test"""
        self.db = TestingSessionLocal()
        # Create test booking
        self.test_booking = BookingModel(
            user_id=1,
            class_schedule_id=1,
            status=BookingStatus.CONFIRMED
        )
        self.db.add(self.test_booking)
        self.db.commit()
        self.db.refresh(self.test_booking)

    def teardown_method(self):
        """Clean up after each test"""
        self.db.close()
        # Drop all tables and recreate them
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    def test_create_booking(self):
        """Test creating a new booking"""
        booking_data = {
            "user_id": 2,
            "class_schedule_id": 2,
            "status": "confirmed"
        }
        response = client.post("/api/v1/bookings/", json=booking_data)
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == booking_data["user_id"]
        assert data["class_schedule_id"] == booking_data["class_schedule_id"]
        assert data["status"] == booking_data["status"]
        assert "id" in data

    def test_read_bookings(self):
        """Test retrieving list of bookings"""
        response = client.get("/api/v1/bookings/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_read_bookings_with_filters(self):
        """Test retrieving bookings with filters"""
        response = client.get("/api/v1/bookings/?user_id=1")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(booking["user_id"] == 1 for booking in data)

    def test_read_booking(self):
        """Test retrieving a single booking"""
        response = client.get(f"/api/v1/bookings/{self.test_booking.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == self.test_booking.id
        assert data["user_id"] == self.test_booking.user_id

    def test_read_nonexistent_booking(self):
        """Test retrieving a non-existent booking"""
        response = client.get("/api/v1/bookings/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Booking not found"

    def test_update_booking(self):
        """Test updating a booking"""
        update_data = {
            "status": "cancelled"
        }
        response = client.put(
            f"/api/v1/bookings/{self.test_booking.id}",
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == update_data["status"]

    def test_update_nonexistent_booking(self):
        """Test updating a non-existent booking"""
        update_data = {
            "status": "cancelled"
        }
        response = client.put("/api/v1/bookings/99999", json=update_data)
        assert response.status_code == 404
        assert response.json()["detail"] == "Booking not found"

    def test_delete_booking(self):
        """Test deleting a booking"""
        response = client.delete(f"/api/v1/bookings/{self.test_booking.id}")
        assert response.status_code == 204

        # Verify booking is deleted
        response = client.get(f"/api/v1/bookings/{self.test_booking.id}")
        assert response.status_code == 404

    def test_delete_nonexistent_booking(self):
        """Test deleting a non-existent booking"""
        response = client.delete("/api/v1/bookings/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Booking not found"

    def test_booking_status_enum(self):
        """Test booking status enum values"""
        valid_statuses = ["confirmed", "cancelled", "completed", "pending"]
        for status in valid_statuses:
            booking_data = {
                "user_id": 3,
                "class_schedule_id": 3,
                "status": status
            }
            response = client.post("/api/v1/bookings/", json=booking_data)
            assert response.status_code == 201
            data = response.json()
            assert data["status"] == status

    def test_invalid_booking_status(self):
        """Test creating booking with invalid status"""
        booking_data = {
            "user_id": 4,
            "class_schedule_id": 4,
            "status": "invalid_status"
        }
        response = client.post("/api/v1/bookings/", json=booking_data)
        assert response.status_code == 422

    def test_booking_pagination(self):
        """Test booking list pagination"""
        # Create multiple bookings
        for i in range(5):
            booking_data = {
                "user_id": 5 + i,
                "class_schedule_id": 5 + i,
                "status": "confirmed"
            }
            client.post("/api/v1/bookings/", json=booking_data)

        # Test pagination
        response = client.get("/api/v1/bookings/?skip=2&limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 3

    def test_booking_filter_by_status(self):
        """Test filtering bookings by status"""
        # Create bookings with different statuses
        client.post("/api/v1/bookings/", json={
            "user_id": 10,
            "class_schedule_id": 10,
            "status": "cancelled"
        })
        client.post("/api/v1/bookings/", json={
            "user_id": 11,
            "class_schedule_id": 11,
            "status": "completed"
        })

        # Test filter
        response = client.get("/api/v1/bookings/?status=cancelled")
        assert response.status_code == 200
        data = response.json()
        assert all(booking["status"] == "cancelled" for booking in data)
