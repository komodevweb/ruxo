"""
Redis caching utilities for fast API responses.
"""
from typing import Optional, Any
from app.services.redis_service import redis_service
import logging

logger = logging.getLogger(__name__)

async def get_cached(key: str) -> Optional[Any]:
    """Get value from Redis cache."""
    if not redis_service.is_enabled():
        return None
    try:
        return await redis_service.get(key)
    except Exception as e:
        logger.error(f"Cache GET error for {key}: {e}")
        return None

async def set_cached(key: str, value: Any, ttl: int = 3600) -> bool:
    """Set value in Redis cache with TTL."""
    if not redis_service.is_enabled():
        return False
    try:
        return await redis_service.set(key, value, ttl=ttl)
    except Exception as e:
        logger.error(f"Cache SET error for {key}: {e}")
        return False

async def invalidate_cache(key: str) -> bool:
    """Invalidate a specific cache key."""
    if not redis_service.is_enabled():
        return False
    try:
        return await redis_service.delete(key)
    except Exception as e:
        logger.error(f"Cache DELETE error for {key}: {e}")
        return False

async def invalidate_user_cache(user_id: str) -> int:
    """Invalidate all cache entries for a specific user."""
    if not redis_service.is_enabled():
        return 0
    try:
        pattern = f"cache:user:{user_id}:*"
        return await redis_service.flush_pattern(pattern)
    except Exception as e:
        logger.error(f"Cache flush error for user {user_id}: {e}")
        return 0

def cache_key(prefix: str, *parts: str) -> str:
    """Generate a cache key from parts."""
    key_parts = [prefix] + [str(p) for p in parts if p]
    return ":".join(key_parts)

