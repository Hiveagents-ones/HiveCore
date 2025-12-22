import redis
import pickle
from typing import Any, Optional, List
from functools import wraps
import time

class RedisCache:
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0):
        self.redis_client = redis.Redis(host=host, port=port, db=db, decode_responses=False)
        self.default_ttl = 3600
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            serialized = pickle.dumps(value)
            if ttl is None:
                ttl = self.default_ttl
            self.redis_client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        try:
            data = self.redis_client.get(key)
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> bool:
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
            return True
        except Exception as e:
            print(f"Cache delete pattern error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        try:
            return self.redis_client.exists(key)
        except Exception as e:
            print(f"Cache exists error: {e}")
            return False

cache_manager = RedisCache()

def multi_layer_cache(prefix: str, ttl: int = 3600):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{prefix}:{str(args)}:{str(kwargs)}"
            
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator

class CacheLayer:
    def __init__(self):
        self.l1_cache = {}  # 内存缓存
        self.l2_cache = RedisCache()  # Redis缓存
    
    def get(self, key: str) -> Optional[Any]:
        # 先查内存缓存
        if key in self.l1_cache:
            item = self.l1_cache[key]
            if time.time() - item['timestamp'] < item['ttl']:
                return item['value']
            else:
                del self.l1_cache[key]
        
        # 再查Redis缓存
        value = self.l2_cache.get(key)
        if value:
            # 回写内存缓存
            self.l1_cache[key] = {
                'value': value,
                'timestamp': time.time(),
                'ttl': 300  # 5分钟
            }
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        # 写入内存缓存
        self.l1_cache[key] = {
            'value': value,
            'timestamp': time.time(),
            'ttl': ttl or 300
        }
        
        # 写入Redis缓存
        self.l2_cache.set(key, value, ttl)
    
    def delete(self, key: str) -> None:
        self.l1_cache.pop(key, None)
        self.l2_cache.delete(key)
    
    def clear_all(self) -> None:
        self.l1_cache.clear()
        self.l2_cache.delete_pattern("*")

multi_cache = CacheLayer()
