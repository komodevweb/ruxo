from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""
    
    def __init__(self, app):
        super().__init__(app)
        self.requests: Dict[str, list] = defaultdict(list)
        self.cleanup_interval = timedelta(minutes=5)
        self.last_cleanup = datetime.utcnow()

    def _cleanup_old_requests(self):
        """Remove old request timestamps to prevent memory leaks."""
        now = datetime.utcnow()
        if now - self.last_cleanup > self.cleanup_interval:
            cutoff_minute = now - timedelta(minutes=1)
            cutoff_hour = now - timedelta(hours=1)
            
            for ip, timestamps in list(self.requests.items()):
                # Keep only recent timestamps
                filtered = [
                    ts for ts in timestamps 
                    if ts > cutoff_hour
                ]
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

    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)
        
        # Skip rate limiting for auth endpoints (login, signup, etc.)
        path = request.url.path
        if "/auth/" in path:
            return await call_next(request)
        
        # Skip rate limiting for job status polling endpoints (read-only, necessary for UI)
        # These endpoints are polled frequently but are safe to exclude
        method = request.method
        
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
        now = datetime.utcnow()
        
        # Cleanup old requests periodically
        self._cleanup_old_requests()
        
        # Get request timestamps for this IP
        timestamps = self.requests[client_ip]
        
        # Attack detection: Check for rapid-fire requests (more than 30 requests in 5 seconds)
        # This indicates a potential attack pattern
        five_seconds_ago = now - timedelta(seconds=5)
        recent_five_seconds = [ts for ts in timestamps if ts > five_seconds_ago]
        if len(recent_five_seconds) >= 30:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded: Too many requests in a short time. Please slow down."
            )
        
        # Very lenient per-minute limit (only for write operations)
        # Only check if it's a POST/PUT/DELETE request
        if method in ["POST", "PUT", "DELETE", "PATCH"]:
            minute_ago = now - timedelta(minutes=1)
            recent_minute = [ts for ts in timestamps if ts > minute_ago]
            # Allow up to 100 write operations per minute (very lenient)
            if len(recent_minute) >= 100:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded: Too many write operations. Please slow down."
                )
        
        # Very lenient per-hour limit (only for write operations)
        if method in ["POST", "PUT", "DELETE", "PATCH"]:
            hour_ago = now - timedelta(hours=1)
            recent_hour = [ts for ts in timestamps if ts > hour_ago]
            # Allow up to 5000 write operations per hour (very lenient)
            if len(recent_hour) >= 5000:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded: Too many write operations per hour. Please slow down."
                )
        
        # Record this request
        timestamps.append(now)
        self.requests[client_ip] = timestamps
        
        response = await call_next(request)
        return response

