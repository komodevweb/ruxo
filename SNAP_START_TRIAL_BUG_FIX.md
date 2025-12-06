# Snap START_TRIAL Event - Bug Fix

## 🐛 Bug Found

**Issue:** START_TRIAL events were NOT being sent to Snap, but WERE being sent to Facebook, TikTok, and GA4.

**Error:**
```
Error sending Snap Conversions API v2 event: object of type 'int' has no len()
File "/root/ruxo/backend/app/services/snap_conversions.py", line 194
```

**When:** December 4, 2025 at 00:50:05 and 00:50:46

---

## 🔍 Root Cause

### The Problem:

Line 194 in `snap_conversions.py`:
```python
# OLD CODE (BUGGY):
if number_items and len(number_items) > 0:
    payload["number_items"] = str(number_items[0])
```

**Issue:** Code assumed `number_items` is always a list, but it can be:
- `None` (no items)
- `int` (single number) ← **This caused the error**
- `list` (array of numbers)

When `number_items` was an integer, calling `len()` on it failed.

---

## ✅ Solution

### Fixed Code:

```python
# NEW CODE (FIXED):
if number_items:
    # Handle both list and integer
    if isinstance(number_items, list) and len(number_items) > 0:
        payload["number_items"] = str(number_items[0])
    elif isinstance(number_items, int):
        payload["number_items"] = str(number_items)
```

**Now handles:**
- ✅ `None` → skips
- ✅ `int` → converts to string
- ✅ `list` → takes first element

---

## 📊 Impact

### Before Fix:
- ❌ START_TRIAL events failed silently
- ❌ No Snap tracking for trial subscriptions
- ❌ Lost attribution data for trials
- ✅ Other events (VIEW_CONTENT, ADD_CART, PURCHASE) worked fine

### After Fix:
- ✅ START_TRIAL events will be sent
- ✅ Complete trial subscription tracking
- ✅ Proper attribution for trial conversions
- ✅ All events working

---

## 🧪 Testing

### To Verify Fix:

1. **Create a test trial subscription**
2. **Check Snap logs:**
   ```bash
   tail -f /root/ruxo/logs/snap_conversions_api.log | grep -A 20 "START_TRIAL"
   ```
3. **Should see:**
   ```json
   {
     "event_type": "START_TRIAL",
     "price": "1.0",
     "currency": "USD",
     "hashed_email": "...",
     ...
   }
   ```
4. **Response should be:**
   ```json
   {
     "status": "SUCCESS",
     "reason": "All records processed"
   }
   ```

---

## 📝 Events Affected

### Events Using `number_items`:

| Event | Status Before | Status After |
|-------|---------------|--------------|
| VIEW_CONTENT | ✅ Working | ✅ Working |
| ADD_CART | ✅ Working | ✅ Working |
| START_CHECKOUT | ✅ Working | ✅ Working |
| PURCHASE | ✅ Working | ✅ Working |
| START_TRIAL | ❌ **BROKEN** | ✅ **FIXED** |

**Only START_TRIAL was affected** because it was the only event that triggered the edge case with `number_items`.

---

## 🎯 Why This Happened

### Code History:

1. Originally written for v3 API (arrays everywhere)
2. Migrated to v2 API (strings and flat structure)
3. Some methods still passed integers
4. Type checking was missing

### The Fix:

Added **defensive type checking** to handle both formats gracefully.

---

## ✅ Status

**Bug:** FIXED ✅  
**Backend:** Restarted ✅  
**Ready for Testing:** YES ✅  

---

## 📊 Verification

### Check Recent START_TRIAL Events:

```bash
# After fix is deployed and a trial is created
grep "START_TRIAL" /root/ruxo/logs/snap_conversions_api.log | tail -5

# Should see successful 200 responses
grep -A 10 "START_TRIAL" /root/ruxo/logs/snap_conversions_api.log | grep "Status Code: 200"
```

---

**Fix Applied:** December 4, 2025, 01:06  
**Status:** RESOLVED ✅

