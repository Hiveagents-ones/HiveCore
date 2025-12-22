import redis
import time
from fastapi import Request, HTTPException
from contextlib import contextmanager
from typing import Optional

class DistributedLock:
    """
    Redis-based distributed lock implementation for FastAPI middleware.
    
    This provides a context manager for acquiring and releasing locks to prevent
    race conditions in concurrent operations like course booking.
    """
    
    def __init__(self, redis_client: redis.Redis, lock_key: str, timeout: int = 30, retry_interval: float = 0.1):
        """
        Initialize the distributed lock.
        
        Args:
            redis_client: Redis client instance
            lock_key: Key to use for the lock in Redis
            timeout: Maximum time to hold the lock (seconds)
            retry_interval: Time between lock acquisition attempts (seconds)
        """
        self.redis = redis_client
        self.lock_key = lock_key
        self.timeout = timeout
        self.retry_interval = retry_interval
        self.identifier = None
    
    @contextmanager
    def acquire(self):
        """
        Context manager for acquiring the lock.
        
        Usage:
            with lock.acquire():
                # critical section
        """
        self.identifier = str(time.time())
        
        # Try to acquire the lock
        end = time.time() + self.timeout
        while time.time() < end:
            if self.redis.setnx(self.lock_key, self.identifier):
                self.redis.expire(self.lock_key, self.timeout)
                try:
                    yield
                finally:
                    self.release()
                return
            time.sleep(self.retry_interval)
        
        raise HTTPException(status_code=429, detail="Could not acquire lock after timeout")
    
    def release(self):
        """Release the lock if it's still held by this instance."""
        if self.identifier:
            # Only release if the lock still belongs to us
            with self.redis.pipeline() as pipe:
                while True:
                    try:
                        pipe.watch(self.lock_key)
                        if pipe.get(self.lock_key) == self.identifier.encode():
                            pipe.multi()
                            pipe.delete(self.lock_key)
                            pipe.execute()
                            break
                        pipe.unwatch()
                        break
                    except redis.exceptions.WatchError:
                        continue


def get_redis_lock(redis_client: redis.Redis, key_prefix: str, request: Request) -> DistributedLock:
    """
    Factory function to create a distributed lock for a specific request.
    
    Args:
        redis_client: Redis client instance
        key_prefix: Prefix for the lock key
        request: FastAPI request object
    
    Returns:
        DistributedLock instance
    """
    # Create a unique lock key based on the request path and user
    user_id = request.headers.get('X-User-ID', 'anonymous')
    path = request.url.path
    lock_key = f"{key_prefix}:{user_id}:{path}"
    
    return DistributedLock(redis_client, lock_key)


# Example usage in FastAPI route:
# @app.post("/book")
# async def book_course(request: Request, redis: redis.Redis = Depends(get_redis)):
#     lock = get_redis_lock(redis, "course_booking", request)
#     with lock.acquire():
#         # Critical section for booking logic
#         pass