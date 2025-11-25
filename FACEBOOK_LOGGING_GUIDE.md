# 📊 Facebook Conversions API - Complete Logging Guide

## 🔍 What You'll See in Logs

Every time a Facebook event is sent, you'll see **detailed logs** showing:
1. ✅ What data is being sent
2. ✅ The complete payload structure
3. ✅ Facebook's response
4. ✅ Success/failure status

---

## 📤 Complete Log Output Example

### When a Purchase Event is Sent

```bash
# Command to watch logs:
sudo journalctl -u ruxo-backend -f | grep -A 50 "FACEBOOK"
```

### Example Output:

```log
================================================================================
💰 [PURCHASE TRACKING] Starting Facebook Purchase event tracking
💰 [PURCHASE TRACKING] User: user@example.com (ID: 550e8400-e29b-41d4-a716-446655440000)
💰 [PURCHASE TRACKING] Name: John Doe
💰 [PURCHASE TRACKING] Plan: pro_monthly
💰 [PURCHASE TRACKING] Value: $39.0 USD
💰 [PURCHASE TRACKING] Event ID: cs_test_a1b2c3d4e5f6
💰 [PURCHASE TRACKING] Event Source URL: https://ruxo.ai/
💰 [PURCHASE TRACKING] Tracking Context: IP=203.0.113.50, UA=Mozilla/5.0 (Windows NT 10.0; Win64; x64)..., fbp=fb.1.1732531200.123456, fbc=fb.1.1732531200.IwAR1234
💰 Purchase Event Details: value=39.0, currency=USD, user=7d8b7f0d91..., external_id=550e8400-e29b-41d4-a716-446655440000
📊 Purchase User Data Fields:
  - em (email): ✓
  - fn (first name): ✓
  - ln (last name): ✓
  - external_id: ✓
  - client_ip_address: ✓
  - client_user_agent: ✓
  - fbp: ✓
  - fbc: ✓
================================================================================
📤 [FACEBOOK API] Sending Purchase event to Facebook Conversions API
📤 [FACEBOOK API] URL: https://graph.facebook.com/v21.0/1891419421775375/events
📤 [FACEBOOK API] Payload (with masked token):
{
  "data": [
    {
      "event_name": "Purchase",
      "event_time": 1732556400,
      "action_source": "website",
      "event_source_url": "https://ruxo.ai/",
      "event_id": "cs_test_a1b2c3d4e5f6",
      "user_data": {
        "em": "7d8b7f0d91f0e4c2f1e8b6c9d2a5b3f1c4e7d8b9a0c1d2e3f4a5b6c7d8e9f0a1",
        "fn": "a3f2e1d4c5b6a7f8e9d0c1b2a3f4e5d6c7b8a9f0e1d2c3b4a5f6e7d8c9a0b1c2",
        "ln": "b4f3e2d5c6b7a8f9e0d1c2b3a4f5e6d7c8b9a0f1e2d3c4b5a6f7e8d9a0b1c2d3",
        "external_id": "550e8400-e29b-41d4-a716-446655440000",
        "client_ip_address": "203.0.113.50",
        "client_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "fbp": "fb.1.1732531200.123456",
        "fbc": "fb.1.1732531200.IwAR1234567890"
      },
      "custom_data": {
        "currency": "USD",
        "value": 39.0
      }
    }
  ],
  "access_token": "EAALqzB8Y...xyz123"
}
================================================================================
📥 [FACEBOOK API] Response from Facebook:
📥 [FACEBOOK API] Status Code: 200
📥 [FACEBOOK API] Response Body:
{
  "events_received": 1,
  "messages": [],
  "fbtrace_id": "AbCdEfGhIjKlMnOpQrStUvWxYz"
}
================================================================================
Successfully sent Purchase event to Facebook Conversions API. Events received: 1
✅ [PURCHASE TRACKING] Purchase event triggered successfully
================================================================================
```

---

## 📋 Breaking Down the Logs

### 1. **Preparation Phase** (Lines 1-17)
```log
💰 [PURCHASE TRACKING] Starting Facebook Purchase event tracking
💰 [PURCHASE TRACKING] User: user@example.com
💰 [PURCHASE TRACKING] Value: $39.0 USD
```

**Shows**:
- User email (raw, not hashed yet)
- Purchase amount and currency
- Event ID for deduplication

---

### 2. **Parameter Verification** (Lines 9-17)
```log
📊 Purchase User Data Fields:
  - em (email): ✓
  - fn (first name): ✓
  - ln (last name): ✓
  - external_id: ✓
  - client_ip_address: ✓
  - client_user_agent: ✓
  - fbp: ✓
  - fbc: ✓
```

**Shows**: Which of the 8 key parameters are present (✓) or missing (✗)

---

### 3. **Outgoing Request** (Lines 18-52)
```log
📤 [FACEBOOK API] Sending Purchase event to Facebook Conversions API
📤 [FACEBOOK API] URL: https://graph.facebook.com/v21.0/1891419421775375/events
📤 [FACEBOOK API] Payload (with masked token):
{
  "data": [
    {
      "event_name": "Purchase",
      "event_time": 1732556400,
      "action_source": "website",
      "event_source_url": "https://ruxo.ai/",
      "event_id": "cs_test_a1b2c3d4e5f6",
      "user_data": {
        "em": "7d8b7f0d91f0e4c2f1e8b6c9...",  // ✅ SHA-256 hashed email
        "fn": "a3f2e1d4c5b6a7f8e9d0c1b2...",  // ✅ SHA-256 hashed first name
        "ln": "b4f3e2d5c6b7a8f9e0d1c2b3...",  // ✅ SHA-256 hashed last name
        "external_id": "550e8400-e29b-41d4-a716-446655440000",  // ✅ NOT hashed
        "client_ip_address": "203.0.113.50",  // ✅ Real IP (not hashed)
        "client_user_agent": "Mozilla/5.0...",  // ✅ Real UA (not hashed)
        "fbp": "fb.1.1732531200.123456",  // ✅ Facebook cookie (not hashed)
        "fbc": "fb.1.1732531200.IwAR1234567890"  // ✅ Click ID (not hashed)
      },
      "custom_data": {
        "currency": "USD",
        "value": 39.0
      }
    }
  ],
  "access_token": "EAALqzB8Y...xyz123"  // ✅ MASKED in logs for security
}
```

**Shows**: 
- Exact URL being called
- Complete JSON payload being sent
- All user_data fields (you can see hashed vs non-hashed)
- Access token is masked for security

---

### 4. **Facebook's Response** (Lines 53-62)
```log
📥 [FACEBOOK API] Response from Facebook:
📥 [FACEBOOK API] Status Code: 200
📥 [FACEBOOK API] Response Body:
{
  "events_received": 1,
  "messages": [],
  "fbtrace_id": "AbCdEfGhIjKlMnOpQrStUvWxYz"
}
```

**Shows**:
- HTTP status code (200 = success)
- `events_received`: How many events Facebook accepted
- `fbtrace_id`: Facebook's internal trace ID for debugging

---

### 5. **Final Status** (Lines 63-65)
```log
Successfully sent Purchase event to Facebook Conversions API. Events received: 1
✅ [PURCHASE TRACKING] Purchase event triggered successfully
```

**Shows**: Confirmation that event was successfully sent and accepted

---

## 🔍 How to Monitor Logs

### Real-Time Monitoring

```bash
# Watch ALL Facebook API traffic
sudo journalctl -u ruxo-backend -f | grep "FACEBOOK"

# Watch only Purchase events
sudo journalctl -u ruxo-backend -f | grep "PURCHASE TRACKING"

# Watch payload being sent
sudo journalctl -u ruxo-backend -f | grep -A 30 "📤 \[FACEBOOK API\] Payload"

# Watch Facebook responses
sudo journalctl -u ruxo-backend -f | grep -A 10 "📥 \[FACEBOOK API\] Response"
```

### Check Historical Logs

```bash
# Last 100 Facebook events
sudo journalctl -u ruxo-backend -n 1000 | grep "FACEBOOK API" | tail -100

# All Purchase events from last hour
sudo journalctl -u ruxo-backend --since "1 hour ago" | grep "Purchase event"

# Count successful sends today
sudo journalctl -u ruxo-backend --since today | grep "Successfully sent" | wc -l
```

---

## 🎯 What Each Field Means

### Event Object Structure

```json
{
  "event_name": "Purchase",           // ✅ Type of event
  "event_time": 1732556400,           // ✅ Unix timestamp (when event happened)
  "action_source": "website",         // ✅ Source type (always "website" for you)
  "event_source_url": "https://...",  // ✅ Where event occurred
  "event_id": "cs_test_...",          // ✅ For deduplication with Pixel
  
  "user_data": {
    "em": "7d8b7f0d...",              // ✅ Email (SHA-256 hashed)
    "fn": "a3f2e1d4...",              // ✅ First name (SHA-256 hashed)
    "ln": "b4f3e2d5...",              // ✅ Last name (SHA-256 hashed)
    "external_id": "550e8400-...",    // ✅ User UUID (NOT hashed)
    "client_ip_address": "203.0...",  // ✅ Real IP (NOT hashed)
    "client_user_agent": "Mozilla...", // ✅ Browser (NOT hashed)
    "fbp": "fb.1.1732531200.123456",  // ✅ Facebook cookie (NOT hashed)
    "fbc": "fb.1.1732531200.IwAR..."  // ✅ Click ID (NOT hashed)
  },
  
  "custom_data": {
    "currency": "USD",                // ✅ Currency code
    "value": 39.0                     // ✅ Purchase amount
  }
}
```

---

## 🚨 Error Scenarios

### If Facebook Rejects the Event

```log
================================================================================
📥 [FACEBOOK API] Response from Facebook:
📥 [FACEBOOK API] Status Code: 400
📥 [FACEBOOK API] Response Body:
{
  "error": {
    "message": "Invalid user data parameter",
    "type": "OAuthException",
    "code": 100,
    "fbtrace_id": "AbCdEfGhIj"
  }
}
================================================================================
Facebook Conversions API error: {'message': 'Invalid user data parameter', 'type': 'OAuthException', 'code': 100, 'fbtrace_id': 'AbCdEfGhIj'}
Error details - Code: 100, Message: Invalid user data parameter, Type: OAuthException
```

### If Network Fails

```log
HTTP error sending Facebook Conversions API event: Connection timeout
```

---

## 🎯 Verification Checklist

When you see logs, verify:

### ✅ Pre-Send Checks
- [ ] All 8 user_data fields show ✓
- [ ] IP address looks valid (not 127.0.0.1)
- [ ] User agent looks like real browser
- [ ] Email hash is 64 characters (SHA-256)

### ✅ Payload Checks
- [ ] `event_time` is recent Unix timestamp
- [ ] `action_source` is "website"
- [ ] `event_source_url` is your domain
- [ ] `client_ip_address` is real IP (not hashed)
- [ ] `em`, `fn`, `ln` are hashed (64 char hex)
- [ ] `fbp` starts with "fb.1."
- [ ] `custom_data.value` matches purchase amount

### ✅ Response Checks
- [ ] Status code is 200
- [ ] `events_received` is 1
- [ ] Has `fbtrace_id` from Facebook

---

## 📊 Example Commands to Run

### Test Right Now

```bash
# Trigger a test event and watch logs
sudo journalctl -u ruxo-backend -f | grep -E "FACEBOOK|PURCHASE" &

# Then in another terminal, trigger a purchase
# (complete a test purchase or use the test endpoint)
```

### Analyze Past Events

```bash
# How many events sent today?
sudo journalctl -u ruxo-backend --since today | grep "Successfully sent.*event to Facebook" | wc -l

# What were the purchase amounts?
sudo journalctl -u ruxo-backend --since "24 hours ago" | grep "value=" | grep -oP 'value=\K[0-9.]+'

# Were there any errors?
sudo journalctl -u ruxo-backend --since "24 hours ago" | grep "Facebook Conversions API error"
```

---

## 🎉 What Success Looks Like

```log
💰 [PURCHASE TRACKING] Starting Facebook Purchase event tracking
💰 [PURCHASE TRACKING] Tracking Context: IP=203.0.113.50, UA=Mozilla/5.0..., fbp=fb.1.xxx, fbc=fb.1.xxx
📊 Purchase User Data Fields:
  - em (email): ✓
  - fn (first name): ✓
  - ln (last name): ✓
  - external_id: ✓
  - client_ip_address: ✓
  - client_user_agent: ✓
  - fbp: ✓
  - fbc: ✓
📤 [FACEBOOK API] Sending Purchase event to Facebook Conversions API
📥 [FACEBOOK API] Status Code: 200
📥 [FACEBOOK API] Response Body:
{
  "events_received": 1,
  "messages": [],
  "fbtrace_id": "AbCdEfGhIjKlMnOpQrStUvWxYz"
}
Successfully sent Purchase event to Facebook Conversions API. Events received: 1
✅ [PURCHASE TRACKING] Purchase event triggered successfully
```

**All ✓ marks and `events_received: 1` = Perfect!** ✅

---

## 📞 Debugging Tips

### If `events_received: 0`
- Check if email/names are properly formatted before hashing
- Verify IP is not localhost (127.0.0.1)
- Check Facebook Events Manager for error details

### If All Fields Show ✗
- Tracking context wasn't captured at checkout
- User needs to visit `/upgrade` page again
- Check database: `last_checkout_ip` should not be NULL

### If Hash Looks Wrong
- Should be 64 character hexadecimal
- Example: `7d8b7f0d91f0e4c2f1e8b6c9d2a5b3f1c4e7d8b9a0c1d2e3f4a5b6c7d8e9f0a1`
- NOT the raw email/name

---

**Logging Level**: INFO (always visible)  
**Backend Restart**: ✅ Applied and running  
**Status**: 🟢 Ready for monitoring

