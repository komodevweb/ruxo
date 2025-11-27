# 🎯 TikTok Conversion API Implementation Plan

## 📋 Overview

This document outlines the complete implementation plan for TikTok Conversion API (Events API) following the same architecture and patterns used for Facebook Conversion API.

**Goal**: Implement server-side TikTok event tracking with pixel support, comprehensive logging, and 100% parameter coverage similar to our Facebook implementation.

---

## 🔍 Research Summary

### TikTok Conversion API Key Requirements

Based on [TikTok Business API Documentation](https://business-api.tiktok.com/portal/docs?id=1797165504155649&lang=en) and [Events API Guide](https://ads.tiktok.com/help/article/getting-started-events-api):

1. **API Endpoint**: `https://business-api.tiktok.com/open_api/v1.3/event/track/`
2. **Authentication**: Access Token (generated in TikTok Ads Manager)
3. **Pixel ID**: Required (already added: `D4JVLBBC77U4IAHDMKB0`)
4. **Event Deduplication**: Uses `event_id` parameter (same as Facebook)
5. **Data Hashing**: Email, phone, names must be SHA-256 hashed (same as Facebook)

### Key Differences from Facebook

| Feature | Facebook | TikTok |
|---------|----------|--------|
| API URL | `graph.facebook.com/v21.0/{pixel_id}/events` | `business-api.tiktok.com/open_api/v1.3/event/track/` |
| Auth Method | Access Token in payload | Access Token in header (`Access-Token`) |
| Request Format | `{data: [events], access_token}` | `{pixel_code, event, context, properties}` |
| Event Names | Standard (Purchase, CompleteRegistration) | Standard (CompletePayment, CompleteRegistration) |
| User Data Fields | `em`, `fn`, `ln`, `ph`, `external_id` | `email`, `phone_number`, `first_name`, `last_name`, `external_id` |
| Browser ID Cookie | `_fbp` | `_ttp` |
| Click ID Cookie | `_fbc` | `_ttclid` |

---

## 🏗️ Architecture Plan

### 1. Service Layer (`backend/app/services/tiktok_conversions.py`)

**Purpose**: Mirror `facebook_conversions.py` structure for TikTok Events API

**Key Components**:
- `TikTokConversionsService` class
- SHA-256 hashing for PII (email, phone, names)
- Event building methods (CompleteRegistration, InitiateCheckout, Purchase)
- Comprehensive logging to `/root/ruxo/logs/tiktok_conversions_api.log`
- Error handling and retry logic

**Methods to Implement**:
```python
- track_complete_registration()
- track_initiate_checkout()
- track_purchase()
- track_view_content() (optional)
- track_add_to_cart() (optional)
```

### 2. Configuration (`backend/app/core/config.py`)

**Add Environment Variables**:
```python
TIKTOK_PIXEL_ID: Optional[str] = None  # Already have: D4JVLBBC77U4IAHDMKB0
TIKTOK_ACCESS_TOKEN: Optional[str] = None  # Generate from TikTok Ads Manager
```

### 3. Integration Points

**Same locations as Facebook tracking**:

#### A. Authentication (`backend/app/routers/auth.py`)
- **CompleteRegistration**: After user signup (email/password, OAuth)
- **Locations**: 
  - `register()` endpoint
  - `oauth_exchange()` endpoint
  - `complete_registration()` endpoint

#### B. Billing (`backend/app/routers/billing.py`)
- **InitiateCheckout**: When user clicks "Select Plan"
- **Location**: `track_initiate_checkout()` endpoint

#### C. Billing Service (`backend/app/services/billing_service.py`)
- **Purchase**: After successful Stripe payment
- **Locations**:
  - `handle_webhook()` - Stripe webhook handler
  - `create_checkout_session()` - After subscription creation

### 4. Frontend Pixel Support

**Already Implemented**: TikTok Pixel code is in `ui/app/layout.tsx`

**Additional Support Needed**:
- Cookie extraction for `_ttp` (browser ID) and `_ttclid` (click ID)
- Pass cookies to backend tracking endpoints (same pattern as Facebook)

### 5. Logging System

**File**: `/root/ruxo/logs/tiktok_conversions_api.log`

**Format**: Same as Facebook logs
- Request/response logging
- Parameter verification
- Error tracking
- Rotating file handler (50MB, 5 backups)

---

## 📝 Implementation Steps

### Phase 1: Core Service Implementation

#### Step 1.1: Create TikTok Conversions Service
**File**: `backend/app/services/tiktok_conversions.py`

**Tasks**:
- [ ] Create `TikTokConversionsService` class
- [ ] Implement SHA-256 hashing method
- [ ] Implement `_get_user_data()` method (map TikTok field names)
- [ ] Implement `_get_event_data()` method
- [ ] Implement `_get_custom_data()` method
- [ ] Implement `send_event()` method (TikTok API format)
- [ ] Set up dedicated logger with file handler
- [ ] Implement event tracking methods:
  - [ ] `track_complete_registration()`
  - [ ] `track_initiate_checkout()`
  - [ ] `track_purchase()`

**TikTok API Request Format**:
```json
{
  "pixel_code": "D4JVLBBC77U4IAHDMKB0",
  "event": "CompletePayment",
  "event_id": "unique_event_id",
  "timestamp": "2025-11-26T19:00:00Z",
  "context": {
    "user_agent": "...",
    "ip": "...",
    "page": {
      "url": "..."
    }
  },
  "properties": {
    "currency": "USD",
    "value": 29.99
  },
  "partner_name": "Ruxo",
  "user": {
    "email": "hashed_email",
    "phone_number": "hashed_phone",
    "first_name": "hashed_first_name",
    "last_name": "hashed_last_name",
    "external_id": "user_uuid"
  }
}
```

#### Step 1.2: Add Configuration
**File**: `backend/app/core/config.py`

**Tasks**:
- [ ] Add `TIKTOK_PIXEL_ID` setting
- [ ] Add `TIKTOK_ACCESS_TOKEN` setting
- [ ] Update `env.example` with new variables

### Phase 2: Integration with Existing Flows

#### Step 2.1: Authentication Integration
**File**: `backend/app/routers/auth.py`

**Tasks**:
- [ ] Import `TikTokConversionsService`
- [ ] Add TikTok tracking to `register()` endpoint
- [ ] Add TikTok tracking to `oauth_exchange()` endpoint
- [ ] Add TikTok tracking to `complete_registration()` endpoint
- [ ] Extract `_ttp` and `_ttclid` cookies (similar to `_fbp`/`_fbc`)

**Pattern** (same as Facebook):
```python
from app.services.tiktok_conversions import TikTokConversionsService

conversions_service = TikTokConversionsService()
asyncio.create_task(conversions_service.track_complete_registration(
    email=user.email,
    first_name=first_name,
    last_name=last_name,
    external_id=str(user.id),
    client_ip=client_ip,
    client_user_agent=client_user_agent,
    ttp=ttp,  # TikTok browser ID
    ttclid=ttclid,  # TikTok click ID
    event_source_url=f"{settings.FRONTEND_URL}/signup",
    event_id=f"registration_{user.id}_{int(time.time())}",
))
```

#### Step 2.2: Billing Integration
**File**: `backend/app/routers/billing.py`

**Tasks**:
- [ ] Add TikTok tracking to `track_initiate_checkout()` endpoint
- [ ] Extract TikTok cookies from request

**File**: `backend/app/services/billing_service.py`

**Tasks**:
- [ ] Add TikTok tracking to `handle_webhook()` method (Purchase events)
- [ ] Add TikTok tracking to subscription modification flows
- [ ] Use same fallback logic as Facebook (session metadata → subscription metadata → user profile)

### Phase 3: Frontend Cookie Support

#### Step 3.1: Update Frontend Tracking
**File**: `ui/lib/facebookTracking.ts` (or create `tiktokTracking.ts`)

**Tasks**:
- [ ] Create helper functions to extract `_ttp` and `_ttclid` cookies
- [ ] Pass TikTok cookies to backend endpoints
- [ ] Update `AuthContext.tsx` to include TikTok cookies in OAuth flow

**File**: `ui/contexts/AuthContext.tsx`

**Tasks**:
- [ ] Extract `_ttp` cookie (TikTok browser ID)
- [ ] Extract `_ttclid` cookie (TikTok click ID)
- [ ] Include in tracking data sent to backend

### Phase 4: Logging & Monitoring

#### Step 4.1: Logging Setup
**File**: `backend/app/services/tiktok_conversions.py`

**Tasks**:
- [ ] Create dedicated logger: `tiktok_conversions_logger`
- [ ] Set up rotating file handler: `/root/ruxo/logs/tiktok_conversions_api.log`
- [ ] Log all requests/responses (same format as Facebook)
- [ ] Log parameter verification (✓/✗ for each field)
- [ ] Log errors with full context

#### Step 4.2: Documentation
**Files to Create**:
- [ ] `TIKTOK_TRACKING_SETUP.md` - Setup guide
- [ ] `TIKTOK_LOGGING_GUIDE.md` - Logging reference
- [ ] `TIKTOK_CAPI_100_COVERAGE_COMPLETE.md` - Coverage documentation
- [ ] Update `README.md` with TikTok tracking info

### Phase 5: Testing & Validation

#### Step 5.1: Test Scripts
**File**: `backend/scripts/test_tiktok_conversion_tracking.py`

**Tasks**:
- [ ] Create test script (mirror Facebook test script)
- [ ] Test CompleteRegistration event
- [ ] Test InitiateCheckout event
- [ ] Test Purchase event
- [ ] Verify logging output

#### Step 5.2: Integration Testing
**Tasks**:
- [ ] Test signup flow (email/password)
- [ ] Test OAuth signup flow
- [ ] Test checkout initiation
- [ ] Test purchase completion (Stripe webhook)
- [ ] Verify events appear in TikTok Events Manager

---

## 🔧 Technical Details

### TikTok API Endpoint

**URL**: `https://business-api.tiktok.com/open_api/v1.3/event/track/`

**Method**: `POST`

**Headers**:
```
Content-Type: application/json
Access-Token: {your_access_token}
```

### Event Names Mapping

| Facebook Event | TikTok Event | Description |
|---------------|--------------|-------------|
| `CompleteRegistration` | `CompleteRegistration` | User signup |
| `InitiateCheckout` | `InitiateCheckout` | User clicks checkout |
| `Purchase` | `CompletePayment` | Payment completed |
| `ViewContent` | `ViewContent` | Page view |
| `AddToCart` | `AddToCart` | Add to cart |

### User Data Field Mapping

| Facebook Field | TikTok Field | Hash Required |
|---------------|--------------|---------------|
| `em` | `email` | ✅ Yes (SHA-256) |
| `ph` | `phone_number` | ✅ Yes (SHA-256) |
| `fn` | `first_name` | ✅ Yes (SHA-256) |
| `ln` | `last_name` | ✅ Yes (SHA-256) |
| `external_id` | `external_id` | ❌ No |
| `client_ip_address` | `ip` (in context) | ❌ No |
| `client_user_agent` | `user_agent` (in context) | ❌ No |
| `fbp` | `ttp` (cookie) | ❌ No |
| `fbc` | `ttclid` (cookie) | ❌ No |

### Cookie Extraction

**TikTok Cookies**:
- `_ttp`: Browser ID (similar to `_fbp`)
- `_ttclid`: Click ID (similar to `_fbc`)

**Extraction Pattern** (same as Facebook):
```python
# Backend
ttp = request.cookies.get("_ttp")
ttclid = request.cookies.get("_ttclid")

# Frontend
const ttpCookie = document.cookie.split(';').find(c => c.trim().startsWith('_ttp='))
const ttclidCookie = document.cookie.split(';').find(c => c.trim().startsWith('_ttclid='))
```

---

## 📊 Expected Coverage

Following the same pattern as Facebook, we expect:

| Parameter | Expected Coverage | Notes |
|-----------|-------------------|-------|
| Email | 100% | Always available |
| First Name | 100% | Always available |
| Last Name | 90-100% | May be missing for some users |
| External ID | 100% | User UUID |
| IP Address | 95-100% | From request headers |
| User Agent | 95-100% | From request headers |
| TikTok Browser ID (`_ttp`) | 95-100% | Cookie-based |
| TikTok Click ID (`_ttclid`) | 35-50% | Only for TikTok ad clicks |

---

## 🚀 Deployment Checklist

### Pre-Deployment
- [ ] Generate TikTok Access Token from Ads Manager
- [ ] Add `TIKTOK_PIXEL_ID` and `TIKTOK_ACCESS_TOKEN` to `.env`
- [ ] Test TikTok Pixel is firing on frontend
- [ ] Verify cookies `_ttp` and `_ttclid` are being set

### Code Deployment
- [ ] Implement `tiktok_conversions.py` service
- [ ] Add configuration variables
- [ ] Integrate with auth endpoints
- [ ] Integrate with billing endpoints
- [ ] Update frontend cookie extraction
- [ ] Set up logging

### Post-Deployment
- [ ] Run test script to verify events
- [ ] Check TikTok Events Manager for incoming events
- [ ] Monitor logs for errors
- [ ] Verify event deduplication (Pixel + API)
- [ ] Check parameter coverage in TikTok dashboard

---

## 📚 References

1. **TikTok Business API Documentation**: https://business-api.tiktok.com/portal/docs?id=1797165504155649&lang=en
2. **TikTok Events API Getting Started**: https://ads.tiktok.com/help/article/getting-started-events-api
3. **Facebook Implementation Reference**: `/root/ruxo/backend/app/services/facebook_conversions.py`
4. **Facebook Logging Guide**: `/root/ruxo/FACEBOOK_LOGGING_GUIDE.md`

---

## 🎯 Success Criteria

Implementation is successful when:

1. ✅ All three events fire correctly (CompleteRegistration, InitiateCheckout, CompletePayment)
2. ✅ Events appear in TikTok Events Manager within 5 minutes
3. ✅ Parameter coverage matches Facebook (95%+ for IP/UA/ttp, 35-50% for ttclid)
4. ✅ Logs show detailed request/response for each event
5. ✅ No duplicate events (deduplication working with Pixel)
6. ✅ Error handling works (graceful failures, no blocking)

---

## 📝 Next Steps

1. **Start with Phase 1**: Create the core service
2. **Test in isolation**: Use test script before integration
3. **Integrate gradually**: Auth → Billing → Frontend
4. **Monitor closely**: Watch logs and TikTok dashboard
5. **Iterate**: Fix issues as they arise

---

**Created**: November 26, 2025  
**Status**: 📋 Planning Complete - Ready for Implementation  
**Estimated Time**: 4-6 hours for full implementation

