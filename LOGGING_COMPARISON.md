# Facebook CAPI Logging - What You'll See Where

## 🎯 Main Terminal Logs (journalctl / systemctl status)
**Clean, concise summaries - NO JSON**

### What you'll see:
```
📤 Sending Purchase event to Facebook Conversions API
📥 Facebook response: 200 - 1 event(s) received
✅ Purchase event successfully sent
```

### How to view:
```bash
# Real-time logs (clean summaries)
sudo journalctl -u ruxo-backend -f

# Filter for Facebook events only
sudo journalctl -u ruxo-backend -f | grep "Facebook\|event"
```

---

## 📄 Dedicated Facebook Log File
**Full JSON payloads and responses - ALL details**

**Location:** `/root/ruxo/logs/facebook_conversions_api.log`

### What you'll see:
```
====================================================================================================
📤 OUTGOING REQUEST - Purchase Event
URL: https://graph.facebook.com/v21.0/123456789/events
HTTP Method: POST
Request Payload:
{
  "data": [
    {
      "event_name": "Purchase",
      "event_time": 1732577844,
      "action_source": "website",
      "user_data": {
        "em": "abc123...",
        "fn": "def456...",
        "ln": "ghi789...",
        "external_id": "550e8400-e29b-41d4-a716-446655440000",
        "client_ip_address": "123.45.67.89",
        "client_user_agent": "Mozilla/5.0...",
        "fbp": "fb.1.1234567890.1234567890",
        "fbc": "fb.1.1234567890.AbCdEfGh"
      },
      "custom_data": {
        "currency": "USD",
        "value": 29.99
      },
      "event_source_url": "https://ruxo.ai/upgrade",
      "event_id": "cs_123abc_xyz789"
    }
  ],
  "access_token": "EAABzbCS9...****"
}
====================================================================================================
====================================================================================================
📥 INCOMING RESPONSE - Purchase Event
HTTP Status Code: 200
Response Headers: {'content-type': 'application/json', ...}
Response Body:
{
  "events_received": 1,
  "messages": [],
  "fbtrace_id": "AkGx..."
}
====================================================================================================

```

### How to view:
```bash
# Real-time monitoring (full JSON)
tail -f /root/ruxo/logs/facebook_conversions_api.log

# Search for specific events
grep "Purchase Event" /root/ruxo/logs/facebook_conversions_api.log

# Count events sent today
grep "OUTGOING REQUEST" /root/ruxo/logs/facebook_conversions_api.log | grep "$(date +%Y-%m-%d)" | wc -l

# View last 50 lines
tail -50 /root/ruxo/logs/facebook_conversions_api.log
```

---

## 📊 Comparison

| Location | Content | When to Use |
|----------|---------|-------------|
| **Main Terminal** | Clean summaries | Quick status checks, monitoring service health |
| **Dedicated File** | Full JSON details | Debugging, verifying exact data sent, compliance audits |

---

## 🚀 Testing the New Logging

1. **Open two terminals:**

**Terminal 1 - Main logs (clean):**
```bash
sudo journalctl -u ruxo-backend -f | grep "Facebook"
```

**Terminal 2 - Detailed logs (JSON):**
```bash
tail -f /root/ruxo/logs/facebook_conversions_api.log
```

2. **Trigger an event:**
   - Go to: https://ruxo.ai/upgrade
   - Click "Select Plan"
   - Complete test purchase (card: `4242 4242 4242 4242`)

3. **Watch both terminals:**
   - Terminal 1 will show: `✅ Purchase event successfully sent`
   - Terminal 2 will show: Full JSON request and response

---

## ✅ Benefits

- **Main terminal stays clean** - No JSON clutter
- **Dedicated file has everything** - Full audit trail
- **Easy debugging** - Jump to dedicated file when needed
- **Better performance** - Less data in main logs = faster grep
- **Compliance ready** - Full JSON payloads archived for review

---

**Updated:** 2025-11-26 01:37  
**Status:** ✅ Active after backend restart

