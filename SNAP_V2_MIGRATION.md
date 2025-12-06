# Snap Conversions API - Migration to v2

## ✅ Changes Completed

**Date:** December 3, 2025  
**Migration:** v3 → v2 API

---

## 🔄 What Changed

### API Endpoint
```
OLD (v3): https://tr.snapchat.com/v3/{pixel_id}/events
NEW (v2): https://tr.snapchat.com/v2/conversion
```

### Payload Structure

**v3 Format (OLD):**
```json
{
  "data": [{
    "event_name": "VIEW_CONTENT",
    "action_source": "WEB",
    "event_time": 1234567890123,
    "user_data": {
      "em": ["hashed_email"],
      "user_agent": "..."
    },
    "custom_data": {
      "currency": "USD",
      "value": 99.99
    }
  }]
}
```

**v2 Format (NEW):**
```json
{
  "pixel_id": "5bf81ee1-15b1-4dc1-b636-d7dae49b950e",
  "timestamp": "1234567890123",
  "event_type": "VIEW_CONTENT",
  "event_conversion_type": "WEB",
  "hashed_email": "...",
  "user_agent": "...",
  "page_url": "https://example.com",
  "price": "99.99",
  "currency": "USD"
}
```

---

## 📊 Key Differences

| Feature | v3 | v2 |
|---------|----|----|
| **Structure** | Nested (data array) | Flat |
| **Event Name** | `event_name` | `event_type` |
| **Action Source** | `action_source: "WEB"` | `event_conversion_type: "WEB"` |
| **Email** | `user_data.em[]` | `hashed_email` |
| **Phone** | `user_data.ph[]` | `hashed_phone_number` |
| **IP Address** | `user_data.client_ip_address` | `hashed_ip_address` |
| **Page URL** | `event_source_url` | `page_url` |
| **Cookie** | `user_data.cookie1` | `uuid_c1` |
| **External ID** | `user_data.external_id[]` | `client_dedup_id` |
| **Transaction ID** | `event_id` | `transaction_id` |
| **Price** | `custom_data.value` (number) | `price` (string) |
| **Items** | `custom_data.content_ids[]` | `item_ids` (comma-separated) |
| **Timestamp** | `event_time` (number) | `timestamp` (string) |

---

## 🔧 Code Changes

### File: `backend/app/services/snap_conversions.py`

#### 1. Updated Endpoints (Lines 56-68)
```python
# OLD v3
self.api_url = f"https://tr.snapchat.com/v3/{self.pixel_id}/events"

# NEW v2
self.api_url = "https://tr.snapchat.com/v2/conversion"
self.validate_url = "https://tr.snapchat.com/v2/conversion/validate"
```

#### 2. Completely Rewrote `send_event()` Method
- Changed from nested structure to flat payload
- Updated all field names to v2 format
- Converted arrays to comma-separated strings
- Converted numbers to strings where needed
- Added pixel_id directly in payload

#### 3. Authentication Remains Same
```python
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {self.access_token}"
}
```
✅ Bearer token authentication unchanged

---

## 🎯 Event Name Mapping

The event names remain the same:
- ✅ `SIGN_UP`
- ✅ `VIEW_CONTENT`
- ✅ `ADD_CART`
- ✅ `START_CHECKOUT`
- ✅ `PURCHASE`
- ✅ `START_TRIAL`

v2 API accepts these event types directly.

---

## 📝 Testing

### Monitor New v2 Requests:
```bash
tail -f /root/ruxo/logs/snap_conversions_api.log
```

### Look For:
```
[OUT] OUTGOING REQUEST - {EVENT} Event (v2)
URL: https://tr.snapchat.com/v2/conversion
```

### Expected Success Response:
```json
{
  "status": "SUCCESS",
  "reason": "Event has been processed successfully."
}
```

---

## ✅ Advantages of v2

1. **Simpler Structure**
   - Flat payload easier to debug
   - No nested objects

2. **Direct Pixel ID**
   - Pixel ID in payload (not URL)
   - Single endpoint for all pixels

3. **Confirmed Working**
   - User confirmed: "v2 with Bearer Token works"
   - Based on actual testing

---

## 🔒 Security

**Authentication:** Bearer token in Authorization header ✅  
**Token Exposure:** NOT in URL anymore ✅  
**Logging:** Token redacted from logs ✅

---

## 📊 Migration Status

| Component | Status |
|-----------|--------|
| API Endpoint | ✅ Updated to v2 |
| Payload Structure | ✅ Converted to flat format |
| Field Mapping | ✅ All fields mapped |
| Authentication | ✅ Bearer token (unchanged) |
| Logging | ✅ Updated to show v2 |
| Backend Restart | ✅ Applied successfully |

---

## 🚀 Next Steps

1. **Monitor Logs:**
   ```bash
   tail -f /root/ruxo/logs/snap_conversions_api.log
   ```

2. **Verify Events:**
   - Check for "v2" in log messages
   - Confirm 200 status codes
   - Look for SUCCESS responses

3. **Test All Event Types:**
   - VIEW_CONTENT
   - SIGN_UP
   - ADD_CART
   - START_CHECKOUT
   - PURCHASE

---

## 🎉 Result

The Snap Conversions API service has been successfully migrated from v3 to v2 format based on user confirmation that v2 works with Bearer token authentication.

**Backend Status:** ✅ Running with v2 API  
**Ready for Testing:** ✅ Yes


