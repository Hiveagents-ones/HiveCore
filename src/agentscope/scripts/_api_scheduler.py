# -*- coding: utf-8 -*-
"""Zhipu API rate limiter using Redis distributed semaphore.

This module provides a unified rate limiter for Zhipu API calls to prevent
429 errors when multiple agents or Claude Code calls access the API concurrently.

Features:
- Redis-based distributed semaphore for cross-process coordination
- Automatic fallback to local asyncio.Semaphore when Redis unavailable
- Configurable concurrency limits and queue timeouts
- Caller identification for debugging and monitoring

Usage:
    from ._api_scheduler import zhipu_rate_limit

    async with zhipu_rate_limit("agent_llm"):
        resp = await llm(messages)
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncGenerator

if TYPE_CHECKING:
    import redis.asyncio as redis_async

logger = logging.getLogger(__name__)


class ZhipuAPIScheduler:
    """Distributed rate limiter for Zhipu API using Redis semaphore.

    This scheduler ensures that the total number of concurrent API calls
    across all processes doesn't exceed the configured limit.

    Attributes:
        max_concurrent: Maximum number of concurrent API calls allowed.
        queue_timeout: Maximum time (seconds) to wait for a slot.
        redis_prefix: Prefix for Redis keys.
    """

    _instance: "ZhipuAPIScheduler | None" = None
    _instance_lock = asyncio.Lock()
    _init_lock = asyncio.Lock()

    def __init__(
        self,
        max_concurrent: int = 5,
        queue_timeout: int = 120,
        redis_prefix: str = "zhipu_scheduler",
    ) -> None:
        """Initialize the scheduler.

        Args:
            max_concurrent (`int`, optional):
                Maximum concurrent API calls. Defaults to 5.
            queue_timeout (`int`, optional):
                Queue timeout in seconds. Defaults to 120.
            redis_prefix (`str`, optional):
                Redis key prefix. Defaults to "zhipu_scheduler".
        """
        self.max_concurrent = max_concurrent
        self.queue_timeout = queue_timeout
        self.redis_prefix = redis_prefix

        # Redis client (lazy initialized)
        self._redis: "redis_async.Redis | None" = None
        self._redis_available: bool | None = None

        # Local fallback semaphore (always initialized for thread safety)
        self._local_semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrent)

        # Stats
        self._stats = {
            "acquired": 0,
            "released": 0,
            "timeouts": 0,
            "fallback_used": 0,
        }

    @classmethod
    async def get_instance(cls) -> "ZhipuAPIScheduler":
        """Get singleton instance of the scheduler.

        Returns:
            `ZhipuAPIScheduler`: The singleton scheduler instance.
        """
        if cls._instance is None:
            async with cls._instance_lock:
                if cls._instance is None:
                    max_concurrent = int(os.getenv("ZHIPU_MAX_CONCURRENT", "5"))
                    queue_timeout = int(os.getenv("ZHIPU_QUEUE_TIMEOUT", "120"))
                    redis_prefix = os.getenv(
                        "ZHIPU_SCHEDULER_PREFIX", "zhipu_scheduler"
                    )
                    cls._instance = cls(
                        max_concurrent=max_concurrent,
                        queue_timeout=queue_timeout,
                        redis_prefix=redis_prefix,
                    )
                    # Initialize Redis with lock protection
                    async with cls._init_lock:
                        await cls._instance._init_redis()
        return cls._instance

    @classmethod
    def get_instance_sync(cls) -> "ZhipuAPIScheduler":
        """Get singleton instance synchronously (for testing).

        Returns:
            `ZhipuAPIScheduler`: The singleton scheduler instance.
        """
        if cls._instance is None:
            max_concurrent = int(os.getenv("ZHIPU_MAX_CONCURRENT", "5"))
            queue_timeout = int(os.getenv("ZHIPU_QUEUE_TIMEOUT", "120"))
            redis_prefix = os.getenv("ZHIPU_SCHEDULER_PREFIX", "zhipu_scheduler")
            cls._instance = cls(
                max_concurrent=max_concurrent,
                queue_timeout=queue_timeout,
                redis_prefix=redis_prefix,
            )
        return cls._instance

    async def _init_redis(self) -> None:
        """Initialize Redis connection and check availability."""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            import redis.asyncio as redis_async

            self._redis = redis_async.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await self._redis.ping()
            self._redis_available = True
            logger.info(
                "[ZhipuAPIScheduler] Redis connected: %s (max_concurrent=%d)",
                redis_url,
                self.max_concurrent,
            )
        except Exception as e:
            logger.warning(
                "[ZhipuAPIScheduler] Redis unavailable (%s), using local fallback",
                e,
            )
            self._redis_available = False
            self._local_semaphore = asyncio.Semaphore(self.max_concurrent)

    def _get_slot_key(self) -> str:
        """Get Redis key for the semaphore slot counter."""
        return f"{self.redis_prefix}:slots"

    def _get_holder_key(self, holder_id: str) -> str:
        """Get Redis key for a slot holder."""
        return f"{self.redis_prefix}:holder:{holder_id}"

    async def _acquire_redis_slot(self, caller: str) -> str | None:
        """Try to acquire a slot using Redis.

        Args:
            caller: Identifier for the caller.

        Returns:
            `str | None`: Holder ID if acquired, None otherwise.
        """
        if not self._redis:
            return None

        holder_id = f"{caller}:{uuid.uuid4().hex[:8]}"
        slot_key = self._get_slot_key()
        holder_key = self._get_holder_key(holder_id)

        try:
            # Atomic check-and-increment using Lua script
            lua_script = """
            local slots = redis.call('GET', KEYS[1])
            if slots == false then
                slots = 0
            else
                slots = tonumber(slots)
            end
            if slots < tonumber(ARGV[1]) then
                redis.call('INCR', KEYS[1])
                redis.call('SETEX', KEYS[2], 300, ARGV[2])
                return 1
            end
            return 0
            """
            result = await self._redis.eval(
                lua_script,
                2,
                slot_key,
                holder_key,
                str(self.max_concurrent),
                holder_id,
            )
            if result == 1:
                return holder_id
            return None
        except Exception as e:
            logger.warning("[ZhipuAPIScheduler] Redis acquire error: %s", e)
            self._redis_available = False
            return None

    async def _release_redis_slot(self, holder_id: str) -> None:
        """Release a slot in Redis.

        Args:
            holder_id: The holder ID returned from acquire.
        """
        if not self._redis:
            return

        slot_key = self._get_slot_key()
        holder_key = self._get_holder_key(holder_id)

        try:
            # Atomic decrement using Lua script
            lua_script = """
            local exists = redis.call('EXISTS', KEYS[2])
            if exists == 1 then
                redis.call('DEL', KEYS[2])
                local slots = redis.call('DECR', KEYS[1])
                if slots < 0 then
                    redis.call('SET', KEYS[1], 0)
                end
                return 1
            end
            return 0
            """
            await self._redis.eval(lua_script, 2, slot_key, holder_key)
        except Exception as e:
            logger.warning("[ZhipuAPIScheduler] Redis release error: %s", e)

    async def acquire(self, caller: str = "unknown") -> str:
        """Acquire a rate limit slot.

        Args:
            caller (`str`, optional):
                Identifier for the caller. Defaults to "unknown".

        Returns:
            `str`: Holder ID to be used when releasing.

        Raises:
            TimeoutError: If unable to acquire slot within timeout.
        """
        start_time = time.monotonic()
        attempt = 0

        # Ensure Redis is initialized (with lock to prevent multiple init)
        if self._redis_available is None:
            async with self._init_lock:
                if self._redis_available is None:
                    await self._init_redis()

        # Try Redis-based acquisition
        if self._redis_available and self._redis:
            while True:
                holder_id = await self._acquire_redis_slot(caller)
                if holder_id:
                    self._stats["acquired"] += 1
                    logger.debug(
                        "[ZhipuAPIScheduler] Slot acquired: %s (attempt=%d)",
                        holder_id,
                        attempt,
                    )
                    return holder_id

                # Check timeout
                elapsed = time.monotonic() - start_time
                if elapsed >= self.queue_timeout:
                    self._stats["timeouts"] += 1
                    raise TimeoutError(
                        f"[ZhipuAPIScheduler] Timeout waiting for slot "
                        f"(caller={caller}, elapsed={elapsed:.1f}s)"
                    )

                # Exponential backoff with jitter
                attempt += 1
                wait_time = min(0.5 * (1.5 ** min(attempt, 6)), 5.0)
                logger.debug(
                    "[ZhipuAPIScheduler] Slot busy, waiting %.1fs (attempt=%d)",
                    wait_time,
                    attempt,
                )
                await asyncio.sleep(wait_time)

                # Re-check Redis availability
                if not self._redis_available:
                    break

        # Fallback to local semaphore
        self._stats["fallback_used"] += 1

        try:
            await asyncio.wait_for(
                self._local_semaphore.acquire(),
                timeout=self.queue_timeout - (time.monotonic() - start_time),
            )
        except asyncio.TimeoutError:
            self._stats["timeouts"] += 1
            raise TimeoutError(
                f"[ZhipuAPIScheduler] Local timeout waiting for slot (caller={caller})"
            )

        self._stats["acquired"] += 1
        holder_id = f"local:{caller}:{uuid.uuid4().hex[:8]}"
        logger.debug("[ZhipuAPIScheduler] Local slot acquired: %s", holder_id)
        return holder_id

    async def release(self, holder_id: str) -> None:
        """Release a rate limit slot.

        Args:
            holder_id (`str`):
                The holder ID returned from acquire.
        """
        self._stats["released"] += 1

        if holder_id.startswith("local:"):
            # Local semaphore
            if self._local_semaphore:
                self._local_semaphore.release()
            logger.debug("[ZhipuAPIScheduler] Local slot released: %s", holder_id)
        else:
            # Redis semaphore
            await self._release_redis_slot(holder_id)
            logger.debug("[ZhipuAPIScheduler] Redis slot released: %s", holder_id)

    def get_stats(self) -> dict:
        """Get scheduler statistics.

        Returns:
            `dict`: Statistics including acquired, released, timeouts, fallback_used.
        """
        return {
            **self._stats,
            "redis_available": self._redis_available,
            "max_concurrent": self.max_concurrent,
        }

    async def get_current_slots(self) -> int:
        """Get current number of used slots.

        Returns:
            `int`: Number of currently used slots.
        """
        if self._redis_available and self._redis:
            try:
                result = await self._redis.get(self._get_slot_key())
                return int(result) if result else 0
            except Exception:
                pass
        return -1  # Unknown when using local fallback


@asynccontextmanager
async def zhipu_rate_limit(caller: str = "unknown") -> AsyncGenerator[None, None]:
    """Context manager for rate-limited Zhipu API calls.

    This is the primary interface for rate limiting. It ensures that
    the slot is always released, even if an exception occurs.

    Args:
        caller (`str`, optional):
            Identifier for the caller. Defaults to "unknown".

    Yields:
        None

    Raises:
        TimeoutError: If unable to acquire slot within timeout.

    Example:
        async with zhipu_rate_limit("agent_llm"):
            resp = await llm(messages)
    """
    scheduler = await ZhipuAPIScheduler.get_instance()
    holder_id = await scheduler.acquire(caller)
    try:
        yield
    finally:
        await scheduler.release(holder_id)
