import json
import logging
from typing import Any, Optional, Union

import redis.asyncio as redis
from redis.asyncio import Redis

from .config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Redis缓存管理器，支持多种缓存策略"""

    def __init__(self):
        self.redis: Optional[Redis] = None
        self.default_ttl = 3600  # 默认过期时间1小时

    async def connect(self) -> None:
        """建立Redis连接"""
        try:
            self.redis = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10,
            )
            await self.redis.ping()
            logger.info("Redis连接成功")
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            raise

    async def disconnect(self) -> None:
        """关闭Redis连接"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis连接已关闭")

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self.redis:
            await self.connect()
        
        try:
            value = await self.redis.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"获取缓存失败 {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serialize: bool = True
    ) -> bool:
        """设置缓存值"""
        if not self.redis:
            await self.connect()
        
        try:
            if serialize and not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)
            
            expire_time = ttl if ttl is not None else self.default_ttl
            result = await self.redis.setex(key, expire_time, value)
            return result
        except Exception as e:
            logger.error(f"设置缓存失败 {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.redis:
            await self.connect()
        
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"删除缓存失败 {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        if not self.redis:
            await self.connect()
        
        try:
            result = await self.redis.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"检查缓存存在性失败 {key}: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """设置缓存过期时间"""
        if not self.redis:
            await self.connect()
        
        try:
            result = await self.redis.expire(key, ttl)
            return result
        except Exception as e:
            logger.error(f"设置缓存过期时间失败 {key}: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """获取缓存剩余生存时间"""
        if not self.redis:
            await self.connect()
        
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            logger.error(f"获取缓存TTL失败 {key}: {e}")
            return -1

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """递增缓存值"""
        if not self.redis:
            await self.connect()
        
        try:
            return await self.redis.incrby(key, amount)
        except Exception as e:
            logger.error(f"递增缓存失败 {key}: {e}")
            return None

    async def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """递减缓存值"""
        if not self.redis:
            await self.connect()
        
        try:
            return await self.redis.decrby(key, amount)
        except Exception as e:
            logger.error(f"递减缓存失败 {key}: {e}")
            return None

    async def hget(self, name: str, key: str) -> Optional[Any]:
        """获取哈希字段值"""
        if not self.redis:
            await self.connect()
        
        try:
            value = await self.redis.hget(name, key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"获取哈希字段失败 {name}.{key}: {e}")
            return None

    async def hset(
        self,
        name: str,
        key: str,
        value: Any,
        serialize: bool = True
    ) -> bool:
        """设置哈希字段值"""
        if not self.redis:
            await self.connect()
        
        try:
            if serialize and not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)
            result = await self.redis.hset(name, key, value)
            return result
        except Exception as e:
            logger.error(f"设置哈希字段失败 {name}.{key}: {e}")
            return False

    async def hgetall(self, name: str) -> dict:
        """获取整个哈希"""
        if not self.redis:
            await self.connect()
        
        try:
            data = await self.redis.hgetall(name)
            result = {}
            for key, value in data.items():
                try:
                    result[key] = json.loads(value)
                except json.JSONDecodeError:
                    result[key] = value
            return result
        except Exception as e:
            logger.error(f"获取哈希失败 {name}: {e}")
            return {}

    async def hdel(self, name: str, *keys: str) -> bool:
        """删除哈希字段"""
        if not self.redis:
            await self.connect()
        
        try:
            result = await self.redis.hdel(name, *keys)
            return result > 0
        except Exception as e:
            logger.error(f"删除哈希字段失败 {name}: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """按模式清除缓存"""
        if not self.redis:
            await self.connect()
        
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"按模式清除缓存失败 {pattern}: {e}")
            return 0


# 全局缓存管理器实例
cache = CacheManager()


async def init_cache() -> None:
    """初始化缓存连接"""
    await cache.connect()


async def close_cache() -> None:
    """关闭缓存连接"""
    await cache.disconnect()
