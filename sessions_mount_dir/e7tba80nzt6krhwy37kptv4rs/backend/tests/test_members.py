import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.member import Member
from app.services.member_service import register_member

client = TestClient(app)

@pytest.mark.asyncio
async def test_register_success_phone():
    response = client.post("/api/v1/members", json={
        "phone": "13800138000",
        "email": "test@example.com",
        "name": "John Doe"
    })
    assert response.status_code == 201
    data = response.json()
    assert "member_id" in data
    assert data["phone"] == "13800138000"
    assert "member_card" in data
    assert len(data["member_card"]) == 10

@pytest.mark.asyncio
async def test_register_success_email():
    response = client.post("/api/v1/members", json={
        "phone": "13900138000",
        "email": "user@example.com",
        "name": "Jane Smith"
    })
    assert response.status_code == 201

@pytest.mark.asyncio
async def test_register_invalid_phone():
    response = client.post("/api/v1/members", json={
        "phone": "12345",
        "email": "test@example.com",
        "name": "Invalid"
    })
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_register_invalid_email():
    response = client.post("/api/v1/members", json={
        "phone": "13800138000",
        "email": "invalid-email",
        "name": "Invalid"
    })
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_register_duplicate_phone():
    client.post("/api/v1/members", json={
        "phone": "13800138000",
        "email": "test1@example.com",
        "name": "John Doe"
    })
    response = client.post("/api/v1/members", json={
        "phone": "13800138000",
        "email": "test2@example.com",
        "name": "Jane Doe"
    })
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

@pytest.mark.asyncio
async def test_register_duplicate_email():
    client.post("/api/v1/members", json={
        "phone": "13900138000",
        "email": "user@example.com",
        "name": "Jane Smith"
    })
    response = client.post("/api/v1/members", json={
        "phone": "13900138001",
        "email": "user@example.com",
        "name": "Jane Smith 2"
    })
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

@pytest.mark.asyncio
async def test_register_missing_phone():
    response = client.post("/api/v1/members", json={
        "email": "test@example.com",
        "name": "Missing Phone"
    })
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_register_missing_name():
    response = client.post("/api/v1/members", json={
        "phone": "13800138000",
        "email": "test@example.com"
    })
    assert response.status_code == 422