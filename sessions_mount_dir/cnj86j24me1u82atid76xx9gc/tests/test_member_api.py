import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.core.config import get_db
from backend.app.models.base import Base
from backend.app.models.member import Member
from backend.app.models.permission import User, Permission
from backend.app.core.rbac import get_current_user

# Test Database Setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


def override_get_current_user():
    # Return a mock user with all permissions for testing
    return User(id=1, username="testuser", permissions=[Permission(name="member:create"), Permission(name="member:read"), Permission(name="member:update"), Permission(name="member:delete")])


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_test_data():
    db = TestingSessionLocal()
    # Create a test member
    test_member = Member(
        name="Test User",
        phone="12345678901",
        email="test@example.com",
        level="普通会员",
        points=100,
        remaining_membership=12,
        is_active=True,
    )
    db.add(test_member)
    db.commit()
    db.refresh(test_member)
    member_id = test_member.id
    db.close()
    yield member_id
    # Teardown
    db = TestingSessionLocal()
    db.query(Member).delete()
    db.commit()
    db.close()


def test_create_member():
    response = client.post(
        "/api/v1/members/",
        json={
            "name": "John Doe",
            "phone": "98765432109",
            "email": "john.doe@example.com",
            "level": "黄金会员",
            "points": 500,
            "remaining_membership": 24,
            "is_active": True,
            "notes": "Initial member",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "John Doe"
    assert data["phone"] == "98765432109"
    assert data["email"] == "john.doe@example.com"
    assert data["level"] == "黄金会员"
    assert data["points"] == 500
    assert data["remaining_membership"] == 24
    assert data["is_active"] is True
    assert data["notes"] == "Initial member"
    assert "id" in data


def test_create_member_duplicate_phone():
    # First member
    client.post(
        "/api/v1/members/",
        json={
            "name": "Alice",
            "phone": "11122223333",
        },
    )
    # Second member with same phone
    response = client.post(
        "/api/v1/members/",
        json={
            "name": "Bob",
            "phone": "11122223333",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "手机号已被注册"


def test_read_members(setup_test_data):
    response = client.get("/api/v1/members/")
    assert response.status_code == 200
    data = response.json()
    assert "members" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert len(data["members"]) > 0
    # Check if the test member is in the list
    member_names = [member["name"] for member in data["members"]]
    assert "Test User" in member_names


def test_read_members_with_filters(setup_test_data):
    # Filter by level
    response = client.get("/api/v1/members/?level=普通会员")
    assert response.status_code == 200
    data = response.json()
    for member in data["members"]:
        assert member["level"] == "普通会员"

    # Filter by is_active
    response = client.get("/api/v1/members/?is_active=true")
    assert response.status_code == 200
    data = response.json()
    for member in data["members"]:
        assert member["is_active"] is True

    # Pagination
    response = client.get("/api/v1/members/?skip=0&limit=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["members"]) <= 1


def test_read_member(setup_test_data):
    member_id = setup_test_data
    response = client.get(f"/api/v1/members/{member_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == member_id
    assert data["name"] == "Test User"
    assert data["phone"] == "12345678901"


def test_read_member_not_found():
    response = client.get("/api/v1/members/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "会员未找到"


def test_update_member(setup_test_data):
    member_id = setup_test_data
    update_data = {
        "name": "Updated User",
        "email": "updated@example.com",
        "level": "白金会员",
        "points": 200,
        "remaining_membership": 6,
        "is_active": False,
        "notes": "Updated notes",
    }
    response = client.put(f"/api/v1/members/{member_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == member_id
    assert data["name"] == "Updated User"
    assert data["email"] == "updated@example.com"
    assert data["level"] == "白金会员"
    assert data["points"] == 200
    assert data["remaining_membership"] == 6
    assert data["is_active"] is False
    assert data["notes"] == "Updated notes"
    # Phone should remain unchanged
    assert data["phone"] == "12345678901"


def test_update_member_not_found():
    response = client.put(
        "/api/v1/members/99999",
        json={"name": "Ghost"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "会员未找到"


def test_delete_member(setup_test_data):
    # First, create a member to delete
    create_response = client.post(
        "/api/v1/members/",
        json={
            "name": "To Be Deleted",
            "phone": "55555555555",
        },
    )
    assert create_response.status_code == 200
    member_to_delete_id = create_response.json()["id"]

    # Now delete it
    response = client.delete(f"/api/v1/members/{member_to_delete_id}")
    assert response.status_code == 200
    assert response.json()["detail"] == "会员已删除"

    # Verify it's gone
    response = client.get(f"/api/v1/members/{member_to_delete_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "会员未找到"


def test_delete_member_not_found():
    response = client.delete("/api/v1/members/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "会员未找到"
