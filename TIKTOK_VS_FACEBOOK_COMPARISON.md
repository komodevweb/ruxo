# 🔄 TikTok vs Facebook Conversion API - Side-by-Side Comparison

## 📊 Quick Reference

This document shows the exact differences between Facebook and TikTok implementations to help you mirror the Facebook pattern.

---

## 🔧 Configuration

### Environment Variables

| Facebook | TikTok |
|----------|--------|
| `FACEBOOK_PIXEL_ID` | `TIKTOK_PIXEL_ID` |
| `FACEBOOK_ACCESS_TOKEN` | `TIKTOK_ACCESS_TOKEN` |
| Value: `1891419421775375` | Value: `D4JVLBBC77U4IAHDMKB0` ✅ |

### Config File Location
**Both**: `backend/app/core/config.py`

```python
# Facebook (existing)
FACEBOOK_PIXEL_ID: Optional[str] = None
FACEBOOK_ACCESS_TOKEN: Optional[str] = None

# TikTok (to add)
TIKTOK_PIXEL_ID: Optional[str] = None
TIKTOK_ACCESS_TOKEN: Optional[str] = None
```

---

## 🌐 API Endpoints

| Facebook | TikTok |
|----------|--------|
| `https://graph.facebook.com/v21.0/{pixel_id}/events` | `https://business-api.tiktok.com/open_api/v1.3/event/track/` |
| Method: `POST` | Method: `POST` |
| Auth: Token in payload | Auth: Token in header |

### Request Headers

**Facebook**:
```
Content-Type: application/json
```

**TikTok**:
```
Content-Type: application/json
Access-Token: {your_access_token}
```

---

## 📦 Request Payload Format

### Facebook Format

```json
{
  "data": [
    {
      "event_name": "Purchase",
      "event_time": 1732556400,
      "action_source": "website",
      "event_source_url": "https://ruxo.ai/upgrade",
      "event_id": "purchase_123_456",
      "user_data": {
        "em": "hashed_email",
        "fn": "hashed_first_name",
        "ln": "hashed_last_name",
        "external_id": "user_uuid",
        "client_ip_address": "203.0.113.50",
        "client_user_agent": "Mozilla/5.0...",
        "fbp": "fb.1.1732531200.123456",
        "fbc": "fb.1.1732531200.IwAR1234"
      },
      "custom_data": {
        "currency": "USD",
        "value": 29.99
      }
    }
  ],
  "access_token": "EAALqzB8Y..."
}
```

### TikTok Format

```json
{
  "pixel_code": "D4JVLBBC77U4IAHDMKB0",
  "event": "CompletePayment",
  "event_id": "purchase_123_456",
  "timestamp": "2025-11-26T19:00:00Z",
  "context": {
    "user_agent": "Mozilla/5.0...",
    "ip": "203.0.113.50",
    "page": {
      "url": "https://ruxo.ai/upgrade"
    }
  },
  "properties": {
    "currency": "USD",
    "value": 29.99
  },
  "partner_name": "Ruxo",
  "user": {
    "email": "hashed_email",
    "first_name": "hashed_first_name",
    "last_name": "hashed_last_name",
    "external_id": "user_uuid"
  }
}
```

**Key Differences**:
- TikTok uses `context` object for IP/UA (not in `user_data`)
- TikTok uses `properties` for custom data (not `custom_data`)
- TikTok uses `user` object (not `user_data`)
- TikTok requires `partner_name` field
- TikTok uses ISO timestamp (not Unix timestamp)

---

## 🎯 Event Names

| Facebook Event | TikTok Event | Use Case |
|----------------|--------------|----------|
| `CompleteRegistration` | `CompleteRegistration` | User signup |
| `InitiateCheckout` | `InitiateCheckout` | Checkout button click |
| `Purchase` | `CompletePayment` | Payment completed |
| `ViewContent` | `ViewContent` | Page view |
| `AddToCart` | `AddToCart` | Add to cart |
| `Lead` | `SubmitForm` | Form submission |

---

## 👤 User Data Fields

### Field Name Mapping

| Facebook Field | TikTok Field | Hash Required | Location |
|----------------|-------------|---------------|----------|
| `em` | `email` | ✅ SHA-256 | `user` object |
| `ph` | `phone_number` | ✅ SHA-256 | `user` object |
| `fn` | `first_name` | ✅ SHA-256 | `user` object |
| `ln` | `last_name` | ✅ SHA-256 | `user` object |
| `external_id` | `external_id` | ❌ No | `user` object |
| `client_ip_address` | `ip` | ❌ No | `context` object |
| `client_user_agent` | `user_agent` | ❌ No | `context` object |
| `fbp` | `ttp` (cookie) | ❌ No | Not in API (cookie only) |
| `fbc` | `ttclid` (cookie) | ❌ No | Not in API (cookie only) |

### Code Comparison

**Facebook**:
```python
user_data = {
    "em": self._hash_value(email),
    "fn": self._hash_value(first_name),
    "ln": self._hash_value(last_name),
    "external_id": external_id,
    "client_ip_address": client_ip,
    "client_user_agent": client_user_agent,
    "fbp": fbp,
    "fbc": fbc,
}
```

**TikTok**:
```python
user = {
    "email": self._hash_value(email),
    "first_name": self._hash_value(first_name),
    "last_name": self._hash_value(last_name),
    "external_id": external_id,
}

context = {
    "ip": client_ip,
    "user_agent": client_user_agent,
    "page": {"url": event_source_url}
}
```

---

## 🍪 Cookie Extraction

### Facebook Cookies

```python
# Backend
fbp = request.cookies.get("_fbp")
fbc = request.cookies.get("_fbc")

# Frontend
const fbpCookie = document.cookie.split(';').find(c => c.trim().startsWith('_fbp='))
const fbcCookie = document.cookie.split(';').find(c => c.trim().startsWith('_fbc='))
```

### TikTok Cookies

```python
# Backend
ttp = request.cookies.get("_ttp")
ttclid = request.cookies.get("_ttclid")

# Frontend
const ttpCookie = document.cookie.split(';').find(c => c.trim().startsWith('_ttp='))
const ttclidCookie = document.cookie.split(';').find(c => c.trim().startsWith('_ttclid='))
```

**Note**: TikTok cookies are NOT sent in API payload (unlike Facebook). They're only used for client-side Pixel deduplication.

---

## 📝 Service Class Structure

### Facebook Service

```python
class FacebookConversionsService:
    def __init__(self):
        self.pixel_id = settings.FACEBOOK_PIXEL_ID
        self.access_token = settings.FACEBOOK_ACCESS_TOKEN
        self.api_url = "https://graph.facebook.com/v21.0"
    
    async def send_event(self, event_name, user_data, event_data, custom_data, event_id):
        payload = {
            "data": [{
                "event_name": event_name,
                "event_time": int(time.time()),
                "action_source": "website",
                "user_data": user_data,
                "custom_data": custom_data,
                "event_id": event_id,
            }],
            "access_token": self.access_token,
        }
        url = f"{self.api_url}/{self.pixel_id}/events"
        # POST with payload
```

### TikTok Service (to implement)

```python
class TikTokConversionsService:
    def __init__(self):
        self.pixel_id = settings.TIKTOK_PIXEL_ID
        self.access_token = settings.TIKTOK_ACCESS_TOKEN
        self.api_url = "https://business-api.tiktok.com/open_api/v1.3/event/track/"
    
    async def send_event(self, event_name, user, context, properties, event_id):
        payload = {
            "pixel_code": self.pixel_id,
            "event": event_name,
            "event_id": event_id,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context,
            "properties": properties,
            "partner_name": "Ruxo",
            "user": user,
        }
        headers = {
            "Content-Type": "application/json",
            "Access-Token": self.access_token,
        }
        # POST with headers
```

---

## 🔗 Integration Points

### Both Use Same Locations

| Location | Facebook | TikTok |
|----------|----------|--------|
| **Auth - Register** | ✅ | ✅ (to add) |
| **Auth - OAuth Exchange** | ✅ | ✅ (to add) |
| **Auth - Complete Registration** | ✅ | ✅ (to add) |
| **Billing - Initiate Checkout** | ✅ | ✅ (to add) |
| **Billing Service - Webhook** | ✅ | ✅ (to add) |
| **Billing Service - Subscription Modify** | ✅ | ✅ (to add) |

### Code Pattern (Same for Both)

```python
# Import
from app.services.facebook_conversions import FacebookConversionsService
from app.services.tiktok_conversions import TikTokConversionsService

# Create services
fb_service = FacebookConversionsService()
tiktok_service = TikTokConversionsService()

# Track events (both)
asyncio.create_task(fb_service.track_purchase(...))
asyncio.create_task(tiktok_service.track_purchase(...))
```

---

## 📊 Logging

### Both Use Same Pattern

| Aspect | Facebook | TikTok |
|--------|----------|--------|
| **Logger Name** | `facebook_conversions_api` | `tiktok_conversions_api` |
| **Log File** | `/root/ruxo/logs/facebook_conversions_api.log` | `/root/ruxo/logs/tiktok_conversions_api.log` |
| **Rotation** | 50MB, 5 backups | 50MB, 5 backups |
| **Format** | Request/Response with payloads | Request/Response with payloads |

### Log Format (Identical)

```python
# Both use same format
logger.info("=" * 100)
logger.info(f"📤 OUTGOING REQUEST - {event_name} Event")
logger.info(f"URL: {api_url}")
logger.info(f"Request Payload:")
logger.info(json.dumps(payload, indent=2))
logger.info("=" * 100)
```

---

## ✅ Response Handling

### Facebook Response

```json
{
  "events_received": 1,
  "messages": [],
  "fbtrace_id": "AbCdEfGhIjKlMnOpQrStUvWxYz"
}
```

**Success Check**: `events_received > 0`

### TikTok Response

```json
{
  "code": 0,
  "message": "OK",
  "request_id": "20251126190000abcdef123456"
}
```

**Success Check**: `code == 0`

---

## 🎯 Event ID Deduplication

### Both Use Same Pattern

**Format**: `{event_type}_{identifier}_{timestamp}`

**Examples**:
- `registration_{user_id}_{timestamp}`
- `purchase_{subscription_id}_{timestamp}`
- `checkout_{user_id}_{timestamp}`

**Purpose**: Prevent duplicate counting when Pixel and API both fire

---

## 📈 Expected Coverage

### Both Should Achieve Similar Coverage

| Parameter | Facebook | TikTok | Notes |
|-----------|----------|--------|-------|
| Email | 100% | 100% | Always available |
| First Name | 100% | 100% | Always available |
| Last Name | 90-100% | 90-100% | May be missing |
| External ID | 100% | 100% | User UUID |
| IP Address | 95-100% | 95-100% | From request |
| User Agent | 95-100% | 95-100% | From request |
| Browser ID | 95-100% | 95-100% | Cookie-based |
| Click ID | 35-50% | 35-50% | Only for ad clicks |

---

## 🚀 Implementation Checklist

### Phase 1: Service
- [ ] Create `tiktok_conversions.py`
- [ ] Implement `TikTokConversionsService` class
- [ ] Add SHA-256 hashing
- [ ] Implement event methods
- [ ] Set up logging

### Phase 2: Config
- [ ] Add `TIKTOK_PIXEL_ID` to config
- [ ] Add `TIKTOK_ACCESS_TOKEN` to config
- [ ] Update `env.example`

### Phase 3: Integration
- [ ] Auth - Register
- [ ] Auth - OAuth
- [ ] Auth - Complete Registration
- [ ] Billing - Initiate Checkout
- [ ] Billing Service - Webhook
- [ ] Billing Service - Subscription Modify

### Phase 4: Frontend
- [ ] Extract `_ttp` cookie
- [ ] Extract `_ttclid` cookie
- [ ] Pass to backend endpoints

### Phase 5: Testing
- [ ] Test CompleteRegistration
- [ ] Test InitiateCheckout
- [ ] Test CompletePayment
- [ ] Verify in TikTok Events Manager

---

## 📚 Reference Files

**Facebook Implementation** (use as template):
- `/root/ruxo/backend/app/services/facebook_conversions.py`
- `/root/ruxo/FACEBOOK_LOGGING_GUIDE.md`
- `/root/ruxo/FACEBOOK_CAPI_100_COVERAGE_COMPLETE.md`

**TikTok Documentation**:
- https://business-api.tiktok.com/portal/docs?id=1797165504155649&lang=en
- https://ads.tiktok.com/help/article/getting-started-events-api

---

**Created**: November 26, 2025  
**Purpose**: Quick reference for implementing TikTok CAPI using Facebook pattern

