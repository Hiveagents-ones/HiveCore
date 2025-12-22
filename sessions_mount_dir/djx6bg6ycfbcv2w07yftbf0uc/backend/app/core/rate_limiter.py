import time
import redis
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from .exceptions import RateLimitExceededError


class RateLimiter:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)

    def is_allowed(
        self,
        key: str,
        limit: int,
        window: int,
        identifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check if the request is allowed based on the rate limit.

        Args:
            key (str): The key to identify the rate limit rule.
            limit (int): The maximum number of requests allowed.
            window (int): The time window in seconds.
            identifier (Optional[str]): Unique identifier (e.g., IP address or user ID).

        Returns:
            Dict[str, Any]: A dictionary containing the result and remaining requests.
        """
        current_time = int(time.time())
        redis_key = f"rate_limit:{key}:{identifier}" if identifier else f"rate_limit:{key}"

        # Use a pipeline to ensure atomicity
        pipeline = self.redis_client.pipeline()
        pipeline.zremrangebyscore(redis_key, 0, current_time - window)
        pipeline.zcard(redis_key)
        pipeline.zadd(redis_key, {str(current_time): current_time})
        pipeline.expire(redis_key, window)
        results = pipeline.execute()

        request_count = results[1]
        remaining = max(0, limit - request_count)

        if request_count >= limit:
            return {"allowed": False, "remaining": remaining}
        return {"allowed": True, "remaining": remaining}

    def check_rate_limit(
        self,
        request: Request,
        limit: int,
        window: int,
        key: str = "default",
        identifier: Optional[str] = None,
    ):
        """
        Check the rate limit for a given request and raise an exception if exceeded.

        Args:
            request (Request): The FastAPI request object.
            limit (int): The maximum number of requests allowed.
            window (int): The time window in seconds.
            key (str): The key to identify the rate limit rule.
            identifier (Optional[str]): Unique identifier (e.g., IP address or user ID).
        """
        if not identifier:
            identifier = request.client.host

        result = self.is_allowed(key=key, limit=limit, window=window, identifier=identifier)
        if not result["allowed"]:
            raise RateLimitExceededError(
                detail="Rate limit exceeded. Try again later.",
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": str(result["remaining"]),
                    "X-RateLimit-Reset": str(int(time.time()) + window),
                },
            )


# Global rate limiter instance
rate_limiter = RateLimiter()
