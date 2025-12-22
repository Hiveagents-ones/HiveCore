import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models import Base
from app.models.member import Member

# Create test database
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


class TestMemberRegistration:
    """Test member registration functionality"""

    def test_register_member_success(self):
        """Test successful member registration"""
        member_data = {
            "name": "John Doe",
            "phone": "13800138000",
            "id_card": "110101199001011234"
        }
        response = client.post("/api/v1/members/register", json=member_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == member_data["name"]
        assert data["phone"] == member_data["phone"]
        assert data["id_card"] == member_data["id_card"]
        assert "id" in data

    def test_register_duplicate_phone(self):
        """Test registration with duplicate phone number"""
        member_data = {
            "name": "Jane Doe",
            "phone": "13800138001",
            "id_card": "110101199002021234"
        }
        # First registration should succeed
        response = client.post("/api/v1/members/register", json=member_data)
        assert response.status_code == 201

        # Second registration with same phone should fail
        member_data["id_card"] = "110101199003031234"
        response = client.post("/api/v1/members/register", json=member_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_register_duplicate_id_card(self):
        """Test registration with duplicate ID card"""
        member_data = {
            "name": "Bob Smith",
            "phone": "13800138002",
            "id_card": "110101199004041234"
        }
        # First registration should succeed
        response = client.post("/api/v1/members/register", json=member_data)
        assert response.status_code == 201

        # Second registration with same ID card should fail
        member_data["phone"] = "13800138003"
        response = client.post("/api/v1/members/register", json=member_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_register_invalid_phone_format(self):
        """Test registration with invalid phone format"""
        member_data = {
            "name": "Alice Johnson",
            "phone": "12345",
            "id_card": "110101199005051234"
        }
        response = client.post("/api/v1/members/register", json=member_data)
        assert response.status_code == 422

    def test_register_invalid_id_card_format(self):
        """Test registration with invalid ID card format"""
        member_data = {
            "name": "Charlie Brown",
            "phone": "13800138004",
            "id_card": "123"
        }
        response = client.post("/api/v1/members/register", json=member_data)
        assert response.status_code == 422

    def test_register_missing_name(self):
        """Test registration without name"""
        member_data = {
            "phone": "13800138005",
            "id_card": "110101199006061234"
        }
        response = client.post("/api/v1/members/register", json=member_data)
        assert response.status_code == 422

    def test_register_missing_phone(self):
        """Test registration without phone"""
        member_data = {
            "name": "David Wilson",
            "id_card": "110101199007071234"
        }
        response = client.post("/api/v1/members/register", json=member_data)
        assert response.status_code == 422

    def test_register_missing_id_card(self):
        """Test registration without ID card"""
        member_data = {
            "name": "Eva Davis",
            "phone": "13800138006"
        }
        response = client.post("/api/v1/members/register", json=member_data)
        assert response.status_code == 422

    def test_register_empty_name(self):
        """Test registration with empty name"""
        member_data = {
            "name": "",
            "phone": "13800138007",
            "id_card": "110101199008081234"
        }
        response = client.post("/api/v1/members/register", json=member_data)
        assert response.status_code == 422

    def test_register_empty_phone(self):
        """Test registration with empty phone"""
        member_data = {
            "name": "Frank Miller",
            "phone": "",
            "id_card": "110101199009091234"
        }
        response = client.post("/api/v1/members/register", json=member_data)
        assert response.status_code == 422

    def test_register_empty_id_card(self):
        """Test registration with empty ID card"""
        member_data = {
            "name": "Grace Lee",
            "phone": "13800138008",
            "id_card": ""
        }
        response = client.post("/api/v1/members/register", json=member_data)
        assert response.status_code == 422


class TestMemberRetrieval:
    """Test member retrieval functionality"""

    def setup_method(self):
        """Setup test data"""
        self.member_data = {
            "name": "Test Member",
            "phone": "13800138009",
            "id_card": "110101199010101234"
        }
        response = client.post("/api/v1/members/register", json=self.member_data)
        self.member_id = response.json()["id"]

    def test_get_member_by_id(self):
        """Test getting member by ID"""
        response = client.get(f"/api/v1/members/{self.member_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == self.member_id
        assert data["name"] == self.member_data["name"]
        assert data["phone"] == self.member_data["phone"]
        assert data["id_card"] == self.member_data["id_card"]

    def test_get_member_by_invalid_id(self):
        """Test getting member with invalid ID"""
        response = client.get("/api/v1/members/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_member_by_phone(self):
        """Test getting member by phone number"""
        response = client.get(f"/api/v1/members/phone/{self.member_data['phone']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == self.member_id
        assert data["name"] == self.member_data["name"]
        assert data["phone"] == self.member_data["phone"]
        assert data["id_card"] == self.member_data["id_card"]

    def test_get_member_by_invalid_phone(self):
        """Test getting member with invalid phone number"""
        response = client.get("/api/v1/members/phone/19999999999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_list_members(self):
        """Test listing all members"""
        # Register another member
        member_data2 = {
            "name": "Another Member",
            "phone": "13800138010",
            "id_card": "110101199011111234"
        }
        client.post("/api/v1/members/register", json=member_data2)

        response = client.get("/api/v1/members/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    def test_list_members_with_pagination(self):
        """Test listing members with pagination"""
        response = client.get("/api/v1/members/?skip=0&limit=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 1


class TestMemberBusinessLogic:
    """Test member business logic"""

    def test_member_id_uniqueness(self):
        """Test that each member gets a unique ID"""
        member_data1 = {
            "name": "Member One",
            "phone": "13800138011",
            "id_card": "110101199012121234"
        }
        member_data2 = {
            "name": "Member Two",
            "phone": "13800138012",
            "id_card": "110101199013131234"
        }

        response1 = client.post("/api/v1/members/register", json=member_data1)
        response2 = client.post("/api/v1/members/register", json=member_data2)

        assert response1.status_code == 201
        assert response2.status_code == 201

        id1 = response1.json()["id"]
        id2 = response2.json()["id"]
        assert id1 != id2

    def test_member_data_persistence(self):
        """Test that member data is properly persisted"""
        member_data = {
            "name": "Persistent Member",
            "phone": "13800138013",
            "id_card": "110101199014141234"
        }

        # Register member
        response = client.post("/api/v1/members/register", json=member_data)
        assert response.status_code == 201
        member_id = response.json()["id"]

        # Retrieve member by ID
        response = client.get(f"/api/v1/members/{member_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == member_data["name"]
        assert data["phone"] == member_data["phone"]
        assert data["id_card"] == member_data["id_card"]

        # Retrieve member by phone
        response = client.get(f"/api/v1/members/phone/{member_data['phone']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == member_id

    def test_concurrent_registration_same_phone(self):
        """Test concurrent registration with same phone number"""
        member_data = {
            "name": "Concurrent Member",
            "phone": "13800138014",
            "id_card": "110101199015151234"
        }

        # First registration should succeed
        response1 = client.post("/api/v1/members/register", json=member_data)
        assert response1.status_code == 201

        # Second registration with same phone should fail
        member_data["id_card"] = "110101199016161234"
        response2 = client.post("/api/v1/members/register", json=member_data)
        assert response2.status_code == 400

    def test_concurrent_registration_same_id_card(self):
        """Test concurrent registration with same ID card"""
        member_data = {
            "name": "Concurrent Member 2",
            "phone": "13800138015",
            "id_card": "110101199017171234"
        }

        # First registration should succeed
        response1 = client.post("/api/v1/members/register", json=member_data)
        assert response1.status_code == 201

        # Second registration with same ID card should fail
        member_data["phone"] = "13800138016"
        response2 = client.post("/api/v1/members/register", json=member_data)
        assert response2.status_code == 400
