"""
Redis service for caching and rate limiting.
"""
import redis.asyncio as redis
from typing import Optional, Any
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisService:
    """Redis service for caching, rate limiting, and session storage."""
    
    _client: Optional[redis.Redis] = None
    _enabled: bool = False
    
    @classmethod
    async def initialize(cls) -> bool:
        """Initialize Redis connection."""
        if not settings.REDIS_ENABLED:
            logger.warning("Redis is disabled in settings")
            return False
        
        if not settings.REDIS_URL:
            logger.warning("Redis URL not configured")
            return False
        
        try:
            cls._client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30
            )
            # Test connection
            await cls._client.ping()
            cls._enabled = True
            logger.info("Redis connection established successfully")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Continuing without Redis.")
            cls._enabled = False
            cls._client = None
            return False
    
    @classmethod
    async def close(cls):
        """Close Redis connection."""
        if cls._client:
            await cls._client.close()
            cls._client = None
            cls._enabled = False
            logger.info("Redis connection closed")
    
    @classmethod
    def is_enabled(cls) -> bool:
        """Check if Redis is enabled and connected."""
        return cls._enabled and cls._client is not None
    
    @classmethod
    async def get(cls, key: str) -> Optional[Any]:
        """Get value from Redis."""
        if not cls.is_enabled():
            return None
        
        try:
            value = await cls._client.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    @classmethod
    async def set(cls, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis with optional TTL."""
        if not cls.is_enabled():
            return False
        
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            ttl = ttl or settings.REDIS_CACHE_TTL
            await cls._client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    @classmethod
    async def delete(cls, key: str) -> bool:
        """Delete key from Redis."""
        if not cls.is_enabled():
            return False
        
        try:
            await cls._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False
    
    @classmethod
    async def exists(cls, key: str) -> bool:
        """Check if key exists in Redis."""
        if not cls.is_enabled():
            return False
        
        try:
            return await cls._client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    @classmethod
    async def increment(cls, key: str, amount: int = 1, ttl: Optional[int] = None) -> Optional[int]:
        """Increment a counter in Redis."""
        if not cls.is_enabled():
            return None
        
        try:
            # Use pipeline for atomic operation
            pipe = cls._client.pipeline()
            pipe.incrby(key, amount)
            if ttl:
                pipe.expire(key, ttl)
            results = await pipe.execute()
            return results[0]
        except Exception as e:
            logger.error(f"Redis INCREMENT error for key {key}: {e}")
            return None
    
    @classmethod
    async def get_counter(cls, key: str) -> int:
        """Get counter value from Redis."""
        if not cls.is_enabled():
            return 0
        
        try:
            value = await cls._client.get(key)
            return int(value) if value else 0
        except Exception as e:
            logger.error(f"Redis GET counter error for key {key}: {e}")
            return 0
    
    @classmethod
    async def expire(cls, key: str, ttl: int) -> bool:
        """Set expiration on a key."""
        if not cls.is_enabled():
            return False
        
        try:
            await cls._client.expire(key, ttl)
            return True
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False
    
    @classmethod
    async def keys(cls, pattern: str) -> list:
        """Get keys matching pattern."""
        if not cls.is_enabled():
            return []
        
        try:
            return await cls._client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis KEYS error for pattern {pattern}: {e}")
            return []
    
    @classmethod
    async def flush_pattern(cls, pattern: str) -> int:
        """Delete all keys matching pattern."""
        if not cls.is_enabled():
            return 0
        
        try:
            keys = await cls.keys(pattern)
            if keys:
                return await cls._client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis FLUSH_PATTERN error for pattern {pattern}: {e}")
            return 0

# Global instance
redis_service = RedisService()

