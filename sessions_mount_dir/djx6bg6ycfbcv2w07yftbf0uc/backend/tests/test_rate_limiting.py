import pytest
import time
from unittest.mock import Mock, patch
from fastapi import Request, HTTPException
from app.core.rate_limiter import RateLimiter, RateLimitExceededError
from app.core.exceptions import RateLimitExceededError as CustomRateLimitExceededError


@pytest.fixture
def mock_redis():
    with patch('app.core.rate_limiter.redis.from_url') as mock_from_url:
        mock_client = Mock()
        mock_from_url.return_value = mock_client
        yield mock_client


@pytest.fixture
def rate_limiter(mock_redis):
    return RateLimiter()


def test_is_allowed_within_limit(rate_limiter, mock_redis):
    mock_redis.pipeline.return_value.execute.return_value = [0, 1, 1, 1]
    result = rate_limiter.is_allowed(key="test", limit=5, window=60, identifier="127.0.0.1")
    assert result["allowed"] is True
    assert result["remaining"] == 4


def test_is_allowed_exceeds_limit(rate_limiter, mock_redis):
    mock_redis.pipeline.return_value.execute.return_value = [0, 5, 1, 1]
    result = rate_limiter.is_allowed(key="test", limit=5, window=60, identifier="127.0.0.1")
    assert result["allowed"] is False
    assert result["remaining"] == 0


def test_check_rate_limit_within_limit(rate_limiter, mock_redis):
    mock_redis.pipeline.return_value.execute.return_value = [0, 1, 1, 1]
    request = Request({"type": "http", "client": ("127.0.0.1", 8000)})
    try:
        rate_limiter.check_rate_limit(request, limit=5, window=60, key="test")
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")


def test_check_rate_limit_exceeds_limit(rate_limiter, mock_redis):
    mock_redis.pipeline.return_value.execute.return_value = [0, 5, 1, 1]
    request = Request({"type": "http", "client": ("127.0.0.1", 8000)})
    with pytest.raises(RateLimitExceededError) as exc_info:
        rate_limiter.check_rate_limit(request, limit=5, window=60, key="test")
    assert exc_info.value.detail == "Rate limit exceeded. Try again later."
    assert "X-RateLimit-Limit" in exc_info.value.headers
    assert "X-RateLimit-Remaining" in exc_info.value.headers
    assert "X-RateLimit-Reset" in exc_info.value.headers


def test_check_rate_limit_custom_identifier(rate_limiter, mock_redis):
    mock_redis.pipeline.return_value.execute.return_value = [0, 1, 1, 1]
    request = Request({"type": "http", "client": ("127.0.0.1", 8000)})
    try:
        rate_limiter.check_rate_limit(request, limit=5, window=60, key="test", identifier="user123")
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")


def test_is_allowed_no_identifier(rate_limiter, mock_redis):
    mock_redis.pipeline.return_value.execute.return_value = [0, 1, 1, 1]
    result = rate_limiter.is_allowed(key="test", limit=5, window=60)
    assert result["allowed"] is True
    assert result["remaining"] == 4


def test_check_rate_limit_no_identifier(rate_limiter, mock_redis):
    mock_redis.pipeline.return_value.execute.return_value = [0, 1, 1, 1]
    request = Request({"type": "http", "client": ("127.0.0.1", 8000)})
    try:
        rate_limiter.check_rate_limit(request, limit=5, window=60, key="test")
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")


def test_is_allowed_remaining_requests_calculation(rate_limiter, mock_redis):
    mock_redis.pipeline.return_value.execute.return_value = [0, 3, 1, 1]
    result = rate_limiter.is_allowed(key="test", limit=5, window=60, identifier="127.0.0.1")
    assert result["remaining"] == 2


def test_check_rate_limit_headers(rate_limiter, mock_redis):
    mock_redis.pipeline.return_value.execute.return_value = [0, 5, 1, 1]
    request = Request({"type": "http", "client": ("127.0.0.1", 8000)})
    with pytest.raises(RateLimitExceededError) as exc_info:
        rate_limiter.check_rate_limit(request, limit=5, window=60, key="test")
    headers = exc_info.value.headers
    assert headers["X-RateLimit-Limit"] == "5"
    assert headers["X-RateLimit-Remaining"] == "0"
    assert int(headers["X-RateLimit-Reset"]) > int(time.time())
