import json
import logging
from typing import Any, Optional, Union

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class CacheClient:
    """Redis缓存客户端封装"""
    
    def __init__(self):
        self._redis: Optional[Redis] = None
        self._settings = get_settings()
    
    async def connect(self) -> None:
        """建立Redis连接"""
        if self._redis is None:
            try:
                self._redis = redis.from_url(
                    self._settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
                # 测试连接
                await self._redis.ping()
                logger.info("Redis连接成功")
            except Exception as e:
                logger.error(f"Redis连接失败: {e}")
                raise
    
    async def disconnect(self) -> None:
        """关闭Redis连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis连接已关闭")
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self._redis:
            await self.connect()
        
        try:
            value = await self._redis.get(key)
            if value is None:
                return None
            
            # 尝试解析JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            logger.error(f"获取缓存失败 key={key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ) -> bool:
        """设置缓存值"""
        if not self._redis:
            await self.connect()
        
        try:
            # 序列化值
            if isinstance(value, (dict, list, tuple)):
                serialized_value = json.dumps(value, ensure_ascii=False)
            else:
                serialized_value = str(value)
            
            # 设置过期时间
            if expire is None:
                expire = self._settings.CACHE_DEFAULT_EXPIRE
            
            result = await self._redis.setex(key, expire, serialized_value)
            return result
        except Exception as e:
            logger.error(f"设置缓存失败 key={key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self._redis:
            await self.connect()
        
        try:
            result = await self._redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"删除缓存失败 key={key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self._redis:
            await self.connect()
        
        try:
            result = await self._redis.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"检查键存在性失败 key={key}: {e}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """设置键的过期时间"""
        if not self._redis:
            await self.connect()
        
        try:
            result = await self._redis.expire(key, seconds)
            return result
        except Exception as e:
            logger.error(f"设置过期时间失败 key={key}: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """获取键的剩余生存时间"""
        if not self._redis:
            await self.connect()
        
        try:
            return await self._redis.ttl(key)
        except Exception as e:
            logger.error(f"获取TTL失败 key={key}: {e}")
            return -1
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """递增计数器"""
        if not self._redis:
            await self.connect()
        
        try:
            return await self._redis.incrby(key, amount)
        except Exception as e:
            logger.error(f"递增计数器失败 key={key}: {e}")
            return None
    
    async def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """递减计数器"""
        if not self._redis:
            await self.connect()
        
        try:
            return await self._redis.decrby(key, amount)
        except Exception as e:
            logger.error(f"递减计数器失败 key={key}: {e}")
            return None
    
    async def hget(self, name: str, key: str) -> Optional[Any]:
        """获取哈希字段值"""
        if not self._redis:
            await self.connect()
        
        try:
            value = await self._redis.hget(name, key)
            if value is None:
                return None
            
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            logger.error(f"获取哈希字段失败 name={name} key={key}: {e}")
            return None
    
    async def hset(
        self,
        name: str,
        key: str,
        value: Any
    ) -> bool:
        """设置哈希字段值"""
        if not self._redis:
            await self.connect()
        
        try:
            if isinstance(value, (dict, list, tuple)):
                serialized_value = json.dumps(value, ensure_ascii=False)
            else:
                serialized_value = str(value)
            
            result = await self._redis.hset(name, key, serialized_value)
            return result
        except Exception as e:
            logger.error(f"设置哈希字段失败 name={name} key={key}: {e}")
            return False
    
    async def hgetall(self, name: str) -> dict:
        """获取所有哈希字段"""
        if not self._redis:
            await self.connect()
        
        try:
            data = await self._redis.hgetall(name)
            result = {}
            for key, value in data.items():
                try:
                    result[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    result[key] = value
            return result
        except Exception as e:
            logger.error(f"获取所有哈希字段失败 name={name}: {e}")
            return {}
    
    async def hdel(self, name: str, *keys: str) -> bool:
        """删除哈希字段"""
        if not self._redis:
            await self.connect()
        
        try:
            result = await self._redis.hdel(name, *keys)
            return result > 0
        except Exception as e:
            logger.error(f"删除哈希字段失败 name={name} keys={keys}: {e}")
            return False


# 全局缓存客户端实例
cache = CacheClient()
