# IP Address Tracking in Facebook Conversions API

## Summary

**Answer: The IP address is extracted from the backend HTTP request, NOT from the Facebook Pixel.**

The client IP is captured on the backend when users make API requests (signup, login, checkout) and then sent to Facebook Conversions API.

## Current Implementation

### 1. IP Extraction on Backend

In all conversion tracking endpoints (`auth.py`, `billing.py`), the IP is extracted like this:

```python
client_ip = request.client.host if request.client else None
```

**Examples:**
- `app/routers/auth.py` - Lines 100, 262, 303, 478, 955
- `app/routers/billing.py` - Lines 53, 176, 215, 258

### 2. IP Sent to Facebook (Not Hashed)

In `app/services/facebook_conversions.py` (lines 54-55):

```python
# Do not hash these fields
if client_ip:
    user_data["client_ip_address"] = client_ip
```

The IP is sent as-is to Facebook (not hashed), along with:
- Hashed PII: email, first name, last name
- Unhashed: IP, user agent, fbp, fbc cookies

### 3. Facebook Pixel vs Backend IP

- **Facebook Pixel**: Runs in the browser, tracks client-side events
- **Backend Conversions API**: Receives IP from HTTP request headers on the server

**They are the SAME IP** because:
1. User's browser makes HTTP request to backend
2. Backend captures IP from that HTTP connection
3. Backend forwards IP to Facebook Conversions API
4. Facebook matches this with Pixel events using `fbp` cookie and `event_id`

## ⚠️ ISSUE: Missing Proxy Header Support

### The Problem

The current code uses `request.client.host`, which gives the **direct connection IP**. If the app is behind:
- Nginx reverse proxy
- Cloudflare
- Load balancer

Then `request.client.host` will return the **proxy's IP**, not the **real user's IP**!

### The Solution

Other parts of the codebase (`app/utils/audit.py` and `app/middleware/rate_limit.py`) correctly handle proxies:

```python
def _get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    # Check for forwarded IP (from proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host if request.client else "unknown"
```

## Recommended Fix

### 1. Create a Utility Function

Create `app/utils/request_helpers.py`:

```python
from fastapi import Request
from typing import Optional

def get_client_ip(request: Request) -> Optional[str]:
    """
    Extract real client IP from request, handling proxies.
    
    Checks in order:
    1. X-Forwarded-For (first IP in chain)
    2. X-Real-IP
    3. Direct connection IP
    """
    if not request:
        return None
    
    # Check for forwarded IP (from Cloudflare, Nginx, etc.)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct connection
    return request.client.host if request.client else None
```

### 2. Update All Conversion Tracking

Replace all instances of:
```python
client_ip = request.client.host if request.client else None
```

With:
```python
from app.utils.request_helpers import get_client_ip

client_ip = get_client_ip(request)
```

### 3. Files to Update

- `app/routers/auth.py` (5 occurrences)
- `app/routers/billing.py` (4 occurrences)

## Why This Matters

### For Facebook Conversions API

Facebook uses the IP address to:
1. **Match users** across Pixel and Conversions API events
2. **Geo-targeting** - determine user's location for ad delivery
3. **Fraud detection** - verify the IP matches expected patterns
4. **Attribution** - connect conversions to ad impressions

### Current Risk

If you're using Cloudflare (which you are), all conversion events are being sent with **Cloudflare's proxy IP** instead of the **real user's IP**. This can:
- ❌ Reduce conversion matching accuracy
- ❌ Hurt geo-targeting
- ❌ Decrease attribution quality
- ❌ Impact ad optimization

## Testing

To verify the current behavior:

```bash
# Check what IP is being sent
curl -H "X-Forwarded-For: 1.2.3.4" https://api.ruxo.ai/api/v1/auth/signup

# Then check backend logs to see if it captured 1.2.3.4 or the Cloudflare IP
```

## Conclusion

**Current State:**
- ✅ IP is captured on backend (correct approach)
- ✅ IP is sent to Facebook (correct approach)
- ❌ IP extraction doesn't handle proxies (needs fixing)

**After Fix:**
- ✅ Real user IP will be extracted from proxy headers
- ✅ Facebook will receive accurate IPs for matching
- ✅ Better conversion attribution and ad optimization

