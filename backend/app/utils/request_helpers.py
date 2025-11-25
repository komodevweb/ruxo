"""
Request helper utilities for extracting client information.
"""
from fastapi import Request
from typing import Optional


def get_client_ip(request: Optional[Request]) -> Optional[str]:
    """
    Extract real client IP from request, handling proxies (Cloudflare, Nginx, etc.).
    
    This is critical for Facebook Conversions API to get accurate user IPs for:
    - Event matching and deduplication
    - Geo-targeting
    - Fraud detection
    - Attribution
    
    Checks in order:
    1. X-Forwarded-For (first IP in chain) - Set by Cloudflare/Nginx
    2. X-Real-IP - Alternative proxy header
    3. Direct connection IP - Fallback if no proxy
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Client IP address string, or None if not available
    """
    if not request:
        return None
    
    # Check for forwarded IP (from Cloudflare, Nginx, load balancer, etc.)
    # X-Forwarded-For can contain multiple IPs: "client, proxy1, proxy2"
    # The first IP is the original client
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    # Check for real IP header (alternative to X-Forwarded-For)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct connection IP (only works if not behind proxy)
    return request.client.host if request.client else None

