import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ..app.main import app, get_db
from ..app.models import Base, Member
from datetime import datetime, timedelta

# Setup test database
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
def setup_test_data():
    """Setup test data for performance testing"""
    db = TestingSessionLocal()
    try:
        # Create test members
        members = []
        for i in range(100):
            member = Member(
                name=f"Test Member {i}",
                contact=f"contact{i}@example.com",
                level="Gold" if i % 2 == 0 else "Silver",
                effective_date=datetime.now(),
                expiry_date=datetime.now() + timedelta(days=365)
            )
            members.append(member)
        db.bulk_save_objects(members)
        db.commit()
        yield
    finally:
        db.query(Member).delete()
        db.commit()
        db.close()

def test_member_list_performance(setup_test_data):
    """Test that member list query responds within 500ms"""
    start_time = time.time()
    response = client.get("/api/v1/members/")
    end_time = time.time()
    
    response_time_ms = (end_time - start_time) * 1000
    
    assert response.status_code == 200
    assert response_time_ms < 500, f"Response time {response_time_ms}ms exceeded 500ms limit"
    assert len(response.json()) == 100

def test_member_list_with_pagination_performance(setup_test_data):
    """Test paginated member list query performance"""
    start_time = time.time()
    response = client.get("/api/v1/members/?skip=0&limit=50")
    end_time = time.time()
    
    response_time_ms = (end_time - start_time) * 1000
    
    assert response.status_code == 200
    assert response_time_ms < 500, f"Response time {response_time_ms}ms exceeded 500ms limit"
    assert len(response.json()) == 50

def test_member_detail_performance(setup_test_data):
    """Test individual member retrieval performance"""
    # First get a member ID
    members_response = client.get("/api/v1/members/")
    member_id = members_response.json()[0]["id"]
    
    start_time = time.time()
    response = client.get(f"/api/v1/members/{member_id}")
    end_time = time.time()
    
    response_time_ms = (end_time - start_time) * 1000
    
    assert response.status_code == 200
    assert response_time_ms < 500, f"Response time {response_time_ms}ms exceeded 500ms limit"
    assert response.json()["id"] == member_id

def test_member_creation_performance():
    """Test member creation performance"""
    start_time = time.time()
    response = client.post(
        "/api/v1/members/",
        params={
            "name": "Performance Test Member",
            "contact": "perf@test.com",
            "level": "Gold"
        }
    )
    end_time = time.time()
    
    response_time_ms = (end_time - start_time) * 1000
    
    assert response.status_code == 201
    assert response_time_ms < 500, f"Response time {response_time_ms}ms exceeded 500ms limit"
    assert response.json()["name"] == "Performance Test Member"

def test_member_level_update_performance(setup_test_data):
    """Test member level update performance"""
    # First get a member ID
    members_response = client.get("/api/v1/members/")
    member_id = members_response.json()[0]["id"]
    
    start_time = time.time()
    response = client.put(
        f"/api/v1/members/{member_id}/level",
        params={"new_level": "Platinum"}
    )
    end_time = time.time()
    
    response_time_ms = (end_time - start_time) * 1000
    
    assert response.status_code == 200
    assert response_time_ms < 500, f"Response time {response_time_ms}ms exceeded 500ms limit"
    assert response.json()["level"] == "Platinum"
