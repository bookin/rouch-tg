"""Cache decorators for knowledge base queries"""
from functools import wraps
from app.cache import get_cache
from app.config import get_settings


def cache_quote(expire: int = None):
    """Cache quote queries with configurable TTL"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            settings = get_settings()
            cache = get_cache()
            
            # Use config TTL if not specified
            ttl = expire if expire is not None else settings.REDIS_QUOTE_CACHE_TTL
            
            # Generate cache key
            key = f"quote:{':'.join(map(str, args))}"
            
            # Try cache
            cached = await cache.get(key)
            if cached is not None:
                return cached
            
            # Execute
            result = await func(self, *args, **kwargs)
            
            # Cache
            await cache.set(key, result, ttl)
            
            return result
        return wrapper
    return decorator


def cache_correlation(expire: int = None):
    """Cache correlation searches with configurable TTL"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, problem: str, limit: int = 3):
            settings = get_settings()
            cache = get_cache()
            
            # Use config TTL if not specified
            ttl = expire if expire is not None else settings.REDIS_CORRELATION_CACHE_TTL
            
            key = f"correlation:{problem}:{limit}"
            
            cached = await cache.get(key)
            if cached is not None:
                return cached
            
            result = await func(self, problem, limit)
            
            await cache.set(key, result, ttl)
            
            return result
        return wrapper
    return decorator
