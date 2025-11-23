"""
Rate limiting middleware using Redis for distributed rate limiting.
Falls back to in-memory storage if Redis is not available.
"""
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.services.redis_service import redis_service
import logging

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with Redis support."""
    
    def __init__(self, app):
        super().__init__(app)
        # Fallback in-memory storage if Redis is not available
        self.requests: Dict[str, List[datetime]] = defaultdict(list)
        self.cleanup_interval = timedelta(minutes=5)
        self.last_cleanup = datetime.utcnow()

    def _cleanup_old_requests(self):
        """Remove old request timestamps to prevent memory leaks (fallback only)."""
        if redis_service.is_enabled():
            return  # Redis handles expiration automatically
        
        now = datetime.utcnow()
        if now - self.last_cleanup > self.cleanup_interval:
            cutoff_hour = now - timedelta(hours=1)
            
            for ip, timestamps in list(self.requests.items()):
                filtered = [ts for ts in timestamps if ts > cutoff_hour]
                if filtered:
                    self.requests[ip] = filtered
                else:
                    del self.requests[ip]
            
            self.last_cleanup = now

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for forwarded IP (from proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"

    async def _check_rate_limit_redis(self, client_ip: str, method: str) -> bool:
        """Check rate limit using Redis."""
        if not redis_service.is_enabled():
            return False
        
        try:
            now = datetime.utcnow()
            
            # Attack detection: Check for rapid-fire requests (more than 30 requests in 5 seconds)
            rapid_key = f"rate_limit:rapid:{client_ip}"
            rapid_count = await redis_service.increment(rapid_key, 1, ttl=5)
            if rapid_count and rapid_count > 30:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded: Too many requests in a short time. Please slow down."
                )
            
            # Only rate limit write operations
            if method in ["POST", "PUT", "DELETE", "PATCH"]:
                # Per-minute limit
                minute_key = f"rate_limit:minute:{client_ip}"
                minute_count = await redis_service.increment(minute_key, 1, ttl=60)
                if minute_count and minute_count > settings.RATE_LIMIT_PER_MINUTE:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded: Too many write operations. Please slow down."
                    )
                
                # Per-hour limit
                hour_key = f"rate_limit:hour:{client_ip}"
                hour_count = await redis_service.increment(hour_key, 1, ttl=3600)
                if hour_count and hour_count > settings.RATE_LIMIT_PER_HOUR:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded: Too many write operations per hour. Please slow down."
                    )
            
            return True
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Redis rate limit check error: {e}")
            return False

    async def _check_rate_limit_memory(self, client_ip: str, method: str) -> bool:
        """Check rate limit using in-memory storage (fallback)."""
        now = datetime.utcnow()
        timestamps = self.requests[client_ip]
        
        # Attack detection: Check for rapid-fire requests (more than 30 requests in 5 seconds)
        five_seconds_ago = now - timedelta(seconds=5)
        recent_five_seconds = [ts for ts in timestamps if ts > five_seconds_ago]
        if len(recent_five_seconds) >= 30:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded: Too many requests in a short time. Please slow down."
            )
        
        # Only rate limit write operations
        if method in ["POST", "PUT", "DELETE", "PATCH"]:
            # Per-minute limit
            minute_ago = now - timedelta(minutes=1)
            recent_minute = [ts for ts in timestamps if ts > minute_ago]
            if len(recent_minute) >= settings.RATE_LIMIT_PER_MINUTE:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded: Too many write operations. Please slow down."
                )
            
            # Per-hour limit
            hour_ago = now - timedelta(hours=1)
            recent_hour = [ts for ts in timestamps if ts > hour_ago]
            if len(recent_hour) >= settings.RATE_LIMIT_PER_HOUR:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded: Too many write operations per hour. Please slow down."
                )
        
        # Record this request
        timestamps.append(now)
        self.requests[client_ip] = timestamps
        
        return True

    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)
        
        # Skip rate limiting for OPTIONS requests (CORS preflight)
        method = request.method
        if method == "OPTIONS":
            return await call_next(request)
        
        # Skip rate limiting for auth endpoints (login, signup, etc.)
        path = request.url.path
        if "/auth/" in path:
            return await call_next(request)
        
        # Skip rate limiting for job status polling endpoints (read-only, necessary for UI)
        
        # Exclude GET requests to job status, listing, and read-only endpoints
        if method == "GET":
            # Status endpoints: /api/v1/{service}/status/{job_id}
            if "/status/" in path:
                return await call_next(request)
            
            # Individual job endpoints: /api/v1/{service}/jobs/{job_id}
            if "/jobs/" in path and path.count("/") >= 4:  # Has job_id in path
                return await call_next(request)
            
            # Job listing endpoints: /api/v1/{service}/jobs (no job_id)
            if path.endswith("/jobs") or "/all-jobs" in path:
                return await call_next(request)
            
            # Calculate credits endpoints (frequently called for UI)
            if "/calculate-credits" in path:
                return await call_next(request)
            
            # Models listing endpoints (frequently called for UI)
            if path.endswith("/models") or "/models" in path:
                return await call_next(request)
            
            # Plans endpoint (frequently called for pricing page)
            if "/billing/plans" in path:
                return await call_next(request)

        client_ip = self._get_client_ip(request)
        
        # Cleanup old requests periodically (fallback only)
        self._cleanup_old_requests()
        
        # Try Redis first, fallback to memory
        try:
            if redis_service.is_enabled():
                await self._check_rate_limit_redis(client_ip, method)
            else:
                await self._check_rate_limit_memory(client_ip, method)
        except HTTPException:
            raise
        
        response = await call_next(request)
        return response
