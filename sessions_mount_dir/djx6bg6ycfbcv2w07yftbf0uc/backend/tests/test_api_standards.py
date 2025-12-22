import pytest
from fastapi.testclient import TestClient
from fastapi import status
from unittest.mock import patch
import time
from typing import Dict, Any

from ..app.main import create_app
from ..app.schemas.response import StandardResponse
from ..app.core.exceptions import BaseCustomException

@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI application."""
    app = create_app()
    return TestClient(app)

def test_standard_response_format(client: TestClient):
    """Test that all API responses follow the standard format."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "success" in data
    assert "message" in data
    assert "data" in data
    assert "timestamp" in data
    assert "request_id" in data
    
    assert data["success"] is True
    assert isinstance(data["data"], dict)
    assert data["data"]["status"] == "ok"

def test_error_response_format(client: TestClient):
    """Test that error responses follow the standard format."""
    response = client.get("/nonexistent-endpoint")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    
    data = response.json()
    assert "success" in data
    assert "message" in data
    assert "error_code" in data
    assert "timestamp" in data
    assert "request_id" in data
    
    assert data["success"] is False
    assert isinstance(data["error_code"], str)

def test_validation_error_format(client: TestClient):
    """Test that validation errors follow the standard format."""
    response = client.post("/api/v1/auth/login", json={"invalid": "data"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    data = response.json()
    assert "success" in data
    assert "message" in data
    assert "error_code" in data
    assert "details" in data
    assert "timestamp" in data
    assert "request_id" in data
    
    assert data["success"] is False
    assert isinstance(data["details"], list)

def test_response_time_within_limits(client: TestClient):
    """Test that API response times are within acceptable limits."""
    start_time = time.time()
    response = client.get("/health")
    end_time = time.time()
    
    response_time = (end_time - start_time) * 1000  # Convert to milliseconds
    assert response.status_code == status.HTTP_200_OK
    assert response_time < 500  # Should respond within 500ms

def test_rate_limiting_headers(client: TestClient):
    """Test that rate limiting headers are present in responses."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    
    headers = response.headers
    assert "X-RateLimit-Limit" in headers
    assert "X-RateLimit-Remaining" in headers
    assert "X-RateLimit-Reset" in headers

def test_cors_headers(client: TestClient):
    """Test that CORS headers are properly set."""
    response = client.options("/health")
    assert response.status_code == status.HTTP_200_OK
    
    headers = response.headers
    assert "access-control-allow-origin" in headers
    assert "access-control-allow-methods" in headers
    assert "access-control-allow-headers" in headers

def test_request_id_header(client: TestClient):
    """Test that each request has a unique request ID."""
    response1 = client.get("/health")
    response2 = client.get("/health")
    
    assert response1.status_code == status.HTTP_200_OK
    assert response2.status_code == status.HTTP_200_OK
    
    data1 = response1.json()
    data2 = response2.json()
    
    assert "request_id" in data1
    assert "request_id" in data2
    assert data1["request_id"] != data2["request_id"]

def test_custom_exception_handling(client: TestClient):
    """Test that custom exceptions are properly handled."""
    with patch("..app.routers.auth.login") as mock_login:
        mock_login.side_effect = BaseCustomException(
            message="Test error",
            error_code="TEST_ERROR"
        )
        
        response = client.post("/api/v1/auth/login", json={
            "username": "test",
            "password": "test"
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "Test error"
        assert data["error_code"] == "TEST_ERROR"

def test_api_versioning(client: TestClient):
    """Test that API versioning is properly implemented."""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_404_NOT_FOUND  # Should not exist
    
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK

def test_content_type_headers(client: TestClient):
    """Test that content-type headers are properly set."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert "application/json" in response.headers["content-type"]

def test_error_code_consistency(client: TestClient):
    """Test that error codes are consistent across endpoints."""
    # Test 404 error
    response = client.get("/nonexistent")
    data = response.json()
    assert data["error_code"] == "NOT_FOUND"
    
    # Test validation error
    response = client.post("/api/v1/auth/login", json={})
    data = response.json()
    assert data["error_code"] == "VALIDATION_ERROR"

def test_response_timestamp_format(client: TestClient):
    """Test that response timestamps are in ISO format."""
    response = client.get("/health")
    data = response.json()
    
    timestamp = data["timestamp"]
    # Should be in ISO 8601 format
    assert "T" in timestamp
    assert timestamp.endswith("Z") or "+" in timestamp or "-" in timestamp

def test_pagination_headers(client: TestClient):
    """Test that pagination headers are present when applicable."""
    # This would test an endpoint that returns paginated results
    # For now, we'll just ensure the health endpoint doesn't have pagination headers
    response = client.get("/health")
    assert "X-Total-Count" not in response.headers
    assert "X-Page" not in response.headers
    assert "X-Per-Page" not in response.headers

def test_api_documentation_availability(client: TestClient):
    """Test that API documentation is available in debug mode."""
    # Test docs endpoint
    response = client.get("/docs")
    # In production, docs might be disabled
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    # Test redoc endpoint
    response = client.get("/redoc")
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

def test_health_check_response(client: TestClient):
    """Test the health check endpoint response."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Service is healthy"
    assert data["data"]["status"] == "ok"
    assert "timestamp" in data
    assert "request_id" in data

def test_concurrent_requests(client: TestClient):
    """Test that the API handles concurrent requests properly."""
    import threading
    import queue
    
    results = queue.Queue()
    
    def make_request():
        response = client.get("/health")
        results.put(response.status_code)
    
    threads = []
    for _ in range(10):
        thread = threading.Thread(target=make_request)
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    # Check all responses
    while not results.empty():
        status_code = results.get()
        assert status_code == status.HTTP_200_OK

def test_large_request_handling(client: TestClient):
    """Test that the API handles large requests properly."""
    large_data = {"data": "x" * 10000}  # 10KB of data
    
    response = client.post("/api/v1/auth/login", json=large_data)
    # Should handle large data gracefully
    assert response.status_code in [
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    ]

def test_malformed_json_handling(client: TestClient):
    """Test that the API handles malformed JSON properly."""
    response = client.post(
        "/api/v1/auth/login",
        data="{invalid json}",
        headers={"content-type": "application/json"}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    data = response.json()
    assert data["success"] is False
    assert "error_code" in data

def test_empty_request_handling(client: TestClient):
    """Test that the API handles empty requests properly."""
    response = client.post("/api/v1/auth/login", data="")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    data = response.json()
    assert data["success"] is False
    assert "error_code" in data

def test_unicode_handling(client: TestClient):
    """Test that the API properly handles Unicode characters."""
    unicode_data = {
        "username": "téstñämé",
        "password": "pàssñørd"
    }
    
    response = client.post("/api/v1/auth/login", json=unicode_data)
    # Should handle Unicode without errors
    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_422_UNPROCESSABLE_ENTITY
    ]
    
    if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        data = response.json()
        assert data["success"] is False
        assert "error_code" in data

def test_special_characters_handling(client: TestClient):
    """Test that the API properly handles special characters."""
    special_chars_data = {
        "username": "test!@#$%^&*()_+-=[]{}|;':,./<>?",
        "password": "pass\"'`\n\r\t"
    }
    
    response = client.post("/api/v1/auth/login", json=special_chars_data)
    # Should handle special characters without errors
    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_422_UNPROCESSABLE_ENTITY
    ]
    
    if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        data = response.json()
        assert data["success"] is False
        assert "error_code" in data
