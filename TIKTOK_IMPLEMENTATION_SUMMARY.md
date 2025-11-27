# 🎯 TikTok Conversion API - Implementation Summary

## 📋 Research Complete ✅

Based on analysis of your Facebook Conversion API implementation and TikTok's official documentation, here's the complete plan for implementing TikTok Conversion API.

---

## 🔍 Key Findings

### 1. **Architecture Pattern** ✅
Your Facebook implementation is excellent and can be mirrored for TikTok:
- Service-based architecture (`facebook_conversions.py` → `tiktok_conversions.py`)
- Comprehensive logging to dedicated files
- Integration at same points (auth, billing, webhooks)
- Triple-fallback tracking context system

### 2. **TikTok API Differences**

| Aspect | Facebook | TikTok |
|--------|----------|--------|
| **API Endpoint** | `graph.facebook.com/v21.0/{pixel_id}/events` | `business-api.tiktok.com/open_api/v1.3/event/track/` |
| **Auth Method** | Token in payload | Token in header (`Access-Token`) |
| **Pixel ID** | `1891419421775375` | `D4JVLBBC77U4IAHDMKB0` ✅ (already added) |
| **Browser Cookie** | `_fbp` | `_ttp` |
| **Click Cookie** | `_fbc` | `_ttclid` |
| **Purchase Event** | `Purchase` | `CompletePayment` |

### 3. **Implementation Points** (Same as Facebook)

✅ **Authentication** (`backend/app/routers/auth.py`):
- `register()` - Email/password signup
- `oauth_exchange()` - OAuth signup
- `complete_registration()` - Registration completion

✅ **Billing** (`backend/app/routers/billing.py`):
- `track_initiate_checkout()` - Checkout button click

✅ **Billing Service** (`backend/app/services/billing_service.py`):
- `handle_webhook()` - Stripe webhook (Purchase events)
- `create_checkout_session()` - Subscription creation

---

## 📝 Implementation Plan

### Phase 1: Core Service (2-3 hours)
**File**: `backend/app/services/tiktok_conversions.py`

**Tasks**:
1. Create `TikTokConversionsService` class
2. Implement SHA-256 hashing (same as Facebook)
3. Implement event building methods
4. Set up logging to `/root/ruxo/logs/tiktok_conversions_api.log`
5. Implement three main events:
   - `track_complete_registration()`
   - `track_initiate_checkout()`
   - `track_purchase()` (uses `CompletePayment` event name)

**Key Code Pattern**:
```python
class TikTokConversionsService:
    def __init__(self):
        self.pixel_id = settings.TIKTOK_PIXEL_ID
        self.access_token = settings.TIKTOK_ACCESS_TOKEN
        self.api_url = "https://business-api.tiktok.com/open_api/v1.3/event/track/"
    
    async def send_event(self, event_name, user_data, event_data, custom_data, event_id):
        # Build TikTok API format
        payload = {
            "pixel_code": self.pixel_id,
            "event": event_name,
            "event_id": event_id,
            "timestamp": datetime.utcnow().isoformat(),
            "context": {
                "user_agent": user_data.get("user_agent"),
                "ip": user_data.get("ip"),
                "page": {"url": event_data.get("event_source_url")}
            },
            "user": {
                "email": hashed_email,
                "first_name": hashed_first_name,
                "last_name": hashed_last_name,
                "external_id": external_id
            }
        }
        # Send with Access-Token header
```

### Phase 2: Configuration (15 minutes)
**File**: `backend/app/core/config.py`

**Add**:
```python
# TikTok Conversions API
TIKTOK_PIXEL_ID: Optional[str] = None  # D4JVLBBC77U4IAHDMKB0
TIKTOK_ACCESS_TOKEN: Optional[str] = None  # Generate from TikTok Ads Manager
```

**File**: `backend/env.example`

**Add**:
```bash
# TikTok Conversions API
TIKTOK_PIXEL_ID=D4JVLBBC77U4IAHDMKB0
TIKTOK_ACCESS_TOKEN=your_access_token_here
```

### Phase 3: Integration (1-2 hours)

#### A. Auth Integration
**File**: `backend/app/routers/auth.py`

**Add TikTok tracking alongside Facebook** (same locations):
- After `register()` success
- After `oauth_exchange()` success  
- In `complete_registration()` endpoint

**Pattern**:
```python
from app.services.tiktok_conversions import TikTokConversionsService

# Extract TikTok cookies
ttp = request.cookies.get("_ttp")
ttclid = request.cookies.get("_ttclid")

# Track event
tiktok_service = TikTokConversionsService()
asyncio.create_task(tiktok_service.track_complete_registration(
    email=user.email,
    first_name=first_name,
    last_name=last_name,
    external_id=str(user.id),
    client_ip=client_ip,
    client_user_agent=client_user_agent,
    ttp=ttp,
    ttclid=ttclid,
    event_source_url=f"{settings.FRONTEND_URL}/signup",
    event_id=f"registration_{user.id}_{int(time.time())}",
))
```

#### B. Billing Integration
**File**: `backend/app/routers/billing.py`

**Add to `track_initiate_checkout()`**:
```python
tiktok_service = TikTokConversionsService()
asyncio.create_task(tiktok_service.track_initiate_checkout(...))
```

**File**: `backend/app/services/billing_service.py`

**Add to `handle_webhook()`** (Purchase events):
```python
# After Facebook tracking
tiktok_service = TikTokConversionsService()
asyncio.create_task(tiktok_service.track_purchase(
    value=plan.amount_cents / 100.0,
    currency="USD",
    email=user.email,
    first_name=first_name,
    last_name=last_name,
    external_id=str(user.id),
    client_ip=client_ip,
    client_user_agent=client_user_agent,
    ttp=ttp,
    ttclid=ttclid,
    event_source_url=f"{settings.FRONTEND_URL}/upgrade",
    event_id=f"purchase_{subscription_id}_{timestamp}",
))
```

### Phase 4: Frontend Cookie Support (30 minutes)

**File**: `ui/contexts/AuthContext.tsx`

**Add TikTok cookie extraction** (alongside Facebook):
```typescript
let ttpCookie: string | null = null;
let ttclidCookie: string | null = null;

try {
  const cookies = document.cookie.split(';');
  for (let cookie of cookies) {
    cookie = cookie.trim();
    if (cookie.startsWith('_ttp=')) {
      ttpCookie = cookie.substring(5);
    } else if (cookie.startsWith('_ttclid=')) {
      ttclidCookie = cookie.substring(8);
    }
  }
} catch (e) {
  console.warn('[OAUTH FRONTEND] Could not read TikTok cookies:', e);
}

// Include in tracking data sent to backend
body: JSON.stringify({
  fbp: fbpCookie,
  fbc: fbcCookie,
  ttp: ttpCookie,      // NEW
  ttclid: ttclidCookie, // NEW
  user_agent: userAgentValue,
}),
```

### Phase 5: Logging & Documentation (1 hour)

**Logging**: Same pattern as Facebook
- Dedicated logger: `tiktok_conversions_logger`
- File: `/root/ruxo/logs/tiktok_conversions_api.log`
- Rotating handler: 50MB, 5 backups
- Log request/response with full payloads

**Documentation Files to Create**:
1. `TIKTOK_TRACKING_SETUP.md` - Setup guide
2. `TIKTOK_LOGGING_GUIDE.md` - Logging reference
3. `TIKTOK_CAPI_100_COVERAGE_COMPLETE.md` - Coverage docs

---

## 🎯 Expected Results

Following the same pattern as Facebook, we expect:

| Parameter | Coverage | Notes |
|-----------|----------|-------|
| Email | 100% | Always available |
| First Name | 100% | Always available |
| Last Name | 90-100% | May be missing |
| External ID | 100% | User UUID |
| IP Address | 95-100% | From request |
| User Agent | 95-100% | From request |
| TikTok Browser ID (`_ttp`) | 95-100% | Cookie-based |
| TikTok Click ID (`_ttclid`) | 35-50% | Only for TikTok ad clicks |

---

## 🚀 Quick Start Checklist

### Before Implementation
- [ ] Get TikTok Access Token from Ads Manager
  - Go to: TikTok Ads Manager → Tools → Events → Manage Web Events
  - Select Pixel → Events API → Generate Access Token
- [ ] Add to `.env`:
  ```bash
  TIKTOK_PIXEL_ID=D4JVLBBC77U4IAHDMKB0
  TIKTOK_ACCESS_TOKEN=your_token_here
  ```

### Implementation Order
1. ✅ Create `tiktok_conversions.py` service
2. ✅ Add config variables
3. ✅ Integrate auth endpoints
4. ✅ Integrate billing endpoints
5. ✅ Update frontend cookie extraction
6. ✅ Test with test script
7. ✅ Deploy and monitor

### After Implementation
- [ ] Test CompleteRegistration event (signup)
- [ ] Test InitiateCheckout event (pricing page)
- [ ] Test CompletePayment event (Stripe webhook)
- [ ] Verify events in TikTok Events Manager
- [ ] Monitor logs for errors
- [ ] Check parameter coverage in TikTok dashboard

---

## 📚 Reference Files

**Your Facebook Implementation** (use as template):
- Service: `/root/ruxo/backend/app/services/facebook_conversions.py`
- Config: `/root/ruxo/backend/app/core/config.py` (lines 94-96)
- Auth Integration: `/root/ruxo/backend/app/routers/auth.py`
- Billing Integration: `/root/ruxo/backend/app/routers/billing.py`
- Logging Guide: `/root/ruxo/FACEBOOK_LOGGING_GUIDE.md`

**TikTok Documentation**:
- API Docs: https://business-api.tiktok.com/portal/docs?id=1797165504155649&lang=en
- Events API Guide: https://ads.tiktok.com/help/article/getting-started-events-api

---

## ✅ Success Criteria

Implementation is successful when:

1. ✅ All three events fire correctly
2. ✅ Events appear in TikTok Events Manager within 5 minutes
3. ✅ Parameter coverage matches Facebook (95%+ for IP/UA/ttp)
4. ✅ Logs show detailed request/response for each event
5. ✅ No duplicate events (deduplication working with Pixel)
6. ✅ Error handling works (graceful failures)

---

## 🎉 Next Steps

1. **Review the detailed plan**: `/root/ruxo/TIKTOK_CONVERSION_API_IMPLEMENTATION_PLAN.md`
2. **Start with Phase 1**: Create the core service
3. **Test incrementally**: Don't deploy everything at once
4. **Monitor closely**: Watch logs and TikTok dashboard

---

**Created**: November 26, 2025  
**Status**: 📋 Research Complete - Ready for Implementation  
**Estimated Time**: 4-6 hours total  
**Priority**: High (mirrors successful Facebook implementation)

