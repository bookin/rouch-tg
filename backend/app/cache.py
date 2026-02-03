"""Redis cache integration"""
import json
from typing import Optional, Any
from datetime import timedelta
import redis.asyncio as redis
from app.config import get_settings


class RedisCache:
    """Async Redis cache wrapper"""
    
    def __init__(self):
        settings = get_settings()
        self.redis: Optional[redis.Redis] = None
        self.redis_url = settings.REDIS_URL
        self._connected = False
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.redis.ping()
            self._connected = True
            print("✅ Redis connected")
        except Exception as e:
            print(f"⚠️  Redis connection failed: {e}")
            self._connected = False
    
    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            self._connected = False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self._connected or not self.redis:
            return None
        
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            print(f"Redis get error: {e}")
        
        return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[int] = None
    ):
        """Set value in cache"""
        if not self._connected or not self.redis:
            return
        
        try:
            serialized = json.dumps(value)
            if expire:
                await self.redis.setex(key, expire, serialized)
            else:
                await self.redis.set(key, serialized)
        except Exception as e:
            print(f"Redis set error: {e}")
    
    async def delete(self, key: str):
        """Delete key from cache"""
        if not self._connected or not self.redis:
            return
        
        try:
            await self.redis.delete(key)
        except Exception as e:
            print(f"Redis delete error: {e}")
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self._connected or not self.redis:
            return False
        
        try:
            return await self.redis.exists(key) > 0
        except Exception:
            return False


# Global cache instance
_cache: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """Get global cache instance"""
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache


async def init_cache():
    """Initialize cache connection"""
    cache = get_cache()
    await cache.connect()


async def close_cache():
    """Close cache connection"""
    cache = get_cache()
    await cache.close()


# Cache decorators
def cache_result(key_prefix: str, expire: int = 3600):
    """Decorator to cache function results"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key
            key = f"{key_prefix}:{':'.join(map(str, args))}"
            
            # Try to get from cache
            cached = await cache.get(key)
            if cached is not None:
                return cached
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache.set(key, result, expire)
            
            return result
        return wrapper
    return decorator
