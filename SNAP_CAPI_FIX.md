# Snap Conversions API - Issue Analysis & Fix

## Problem Identified

Your Snap Conversions API implementation was receiving **401 "Invalid access token"** errors on every request.

### Root Cause

**Incorrect Authentication Method**: The access token was being passed as a query parameter in the URL instead of in the Authorization header.

```python
# ❌ WRONG - Old implementation:
self.api_url = f"https://tr.snapchat.com/v3/{self.pixel_id}/events?access_token={self.access_token}"
headers = {
    "Content-Type": "application/json"
}
```

```python
# ✅ CORRECT - New implementation:
self.api_url = f"https://tr.snapchat.com/v3/{self.pixel_id}/events"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {self.access_token}"
}
```

## Changes Made

### File: `backend/app/services/snap_conversions.py`

1. **Removed access token from URL** (line 61)
   - Changed from: `https://tr.snapchat.com/v3/{pixel_id}/events?access_token={token}`
   - Changed to: `https://tr.snapchat.com/v3/{pixel_id}/events`

2. **Added Authorization header** (line 208)
   - Added `"Authorization": f"Bearer {self.access_token}"` to request headers

## Benefits of This Fix

1. **Security**: Access tokens are no longer exposed in URLs (which get logged in plain text)
2. **Compliance**: Follows REST API best practices and Snap's authentication requirements
3. **Correctness**: Uses the proper OAuth 2.0 Bearer token authentication method

## Next Steps - IMPORTANT

### 1. Verify Your Access Token

The token in your logs appears to be a JWT token. You need to verify you have the correct **long-lived access token** from Snapchat:

**How to get the correct token:**
1. Go to [Snapchat Ads Manager](https://ads.snapchat.com/)
2. Navigate to **Business Details** page
3. Look for **Conversions API** section
4. Generate or copy your **long-lived access token**
5. Update your `.env` file with: `SNAP_ACCESS_TOKEN=your_token_here`

### 2. Token Types

Snapchat uses different token types:
- ❌ **OAuth JWT tokens** - These are short-lived and used for user authentication
- ✅ **Long-lived static tokens** - These are for Conversions API and don't expire

Make sure you're using the **long-lived static token** from Business Manager.

### 3. Test the Fix

After updating your token, restart your backend server:

```bash
# Restart your backend
cd /root/ruxo/backend
# Stop existing process
pkill -f "uvicorn"
# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then monitor the logs:
```bash
tail -f /root/ruxo/logs/snap_conversions_api.log
```

### 4. Expected Success Response

After the fix, you should see:
```json
{
  "status": "VALID",
  "reason": "Events have been processed successfully."
}
```

With HTTP status code **200** instead of **401**.

## Additional Resources

- [Snap Conversions API Docs](https://developers.snap.com/api/marketing-api/Conversions-API/GetStarted)
- [Snap API Parameters](https://developers.snap.com/api/marketing-api/Conversions-API/Parameters)
- [Authentication Guide](https://developers.snap.com/api/marketing-api/Conversions-API/UsingTheAPI)

## Summary

The code has been fixed to use proper Bearer token authentication in the Authorization header. However, **you still need to verify and update your SNAP_ACCESS_TOKEN** environment variable with the correct long-lived token from Snapchat Business Manager for the API to work properly.


