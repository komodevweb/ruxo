# 📁 Facebook Conversions API Dedicated Log File

## 📍 Log File Location

```
/root/ruxo/logs/facebook_conversions_api.log
```

This file contains **ONLY** Facebook Conversions API requests and responses with complete JSON payloads.

---

## 🔍 What's Logged

### Every Facebook Event Includes:

1. **📤 Outgoing Request**
   - Event type (Purchase, InitiateCheckout, CompleteRegistration, etc.)
   - Full URL
   - HTTP method (POST)
   - Complete JSON payload with:
     - All user_data fields (email hashed, IP not hashed, etc.)
     - Event metadata
     - Custom data (for Purchase events)
     - Access token (masked for security)

2. **📥 Incoming Response**
   - HTTP status code
   - Response headers
   - Complete response body from Facebook
   - Success/error messages
   - Facebook trace ID

---

## 📊 View the Logs

### View Latest Events (Real-Time)
```bash
# Watch file in real-time
tail -f /root/ruxo/logs/facebook_conversions_api.log

# Watch with color highlighting
tail -f /root/ruxo/logs/facebook_conversions_api.log | grep --color=always -E "📤|📥|event_name|client_ip|events_received|="
```

### View Complete Log File
```bash
# View entire file
cat /root/ruxo/logs/facebook_conversions_api.log

# View with pagination
less /root/ruxo/logs/facebook_conversions_api.log

# View last 100 lines
tail -n 100 /root/ruxo/logs/facebook_conversions_api.log
```

### Search for Specific Events
```bash
# Find all Purchase events
grep -A 30 "Purchase Event" /root/ruxo/logs/facebook_conversions_api.log

# Find all successful events (events_received: 1)
grep -B 5 '"events_received": 1' /root/ruxo/logs/facebook_conversions_api.log

# Find all errors
grep -A 10 "error" /root/ruxo/logs/facebook_conversions_api.log

# Find events from specific user IP
grep -A 30 "client_ip_address.*203.0.113.50" /root/ruxo/logs/facebook_conversions_api.log
```

### Count Events
```bash
# Count total events sent today
grep "OUTGOING REQUEST" /root/ruxo/logs/facebook_conversions_api.log | wc -l

# Count Purchase events
grep "OUTGOING REQUEST - Purchase Event" /root/ruxo/logs/facebook_conversions_api.log | wc -l

# Count successful events
grep '"events_received": 1' /root/ruxo/logs/facebook_conversions_api.log | wc -l
```

---

## 📋 Example Log Entry

```log
====================================================================================================
2025-11-26 01:24:32 - INFO - 📤 OUTGOING REQUEST - Purchase Event
2025-11-26 01:24:32 - INFO - URL: https://graph.facebook.com/v21.0/1891419421775375/events
2025-11-26 01:24:32 - INFO - HTTP Method: POST
2025-11-26 01:24:32 - INFO - Request Payload:
2025-11-26 01:24:32 - INFO - {
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
        "client_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
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
====================================================================================================
====================================================================================================
2025-11-26 01:24:32 - INFO - 📥 INCOMING RESPONSE - Purchase Event
2025-11-26 01:24:32 - INFO - HTTP Status Code: 200
2025-11-26 01:24:32 - INFO - Response Headers: {'content-type': 'application/json', 'x-fb-trace-id': 'AbCdEfGhIj', ...}
2025-11-26 01:24:32 - INFO - Response Body:
2025-11-26 01:24:32 - INFO - {
  "events_received": 1,
  "messages": [],
  "fbtrace_id": "AbCdEfGhIjKlMnOpQrStUvWxYz"
}
====================================================================================================

```

---

## 🔄 Log Rotation

The log file automatically rotates to prevent disk space issues:

- **Max file size**: 50 MB
- **Backup files**: Keeps 5 old files
- **Total max size**: 250 MB (50 MB × 5 files)

When the log reaches 50 MB, it automatically:
1. Renames current file to `facebook_conversions_api.log.1`
2. Creates new `facebook_conversions_api.log`
3. Keeps up to 5 backup files (`.1`, `.2`, `.3`, `.4`, `.5`)

### View All Log Files
```bash
ls -lh /root/ruxo/logs/facebook_conversions_api.log*
```

### View Old Logs
```bash
# View previous log file
cat /root/ruxo/logs/facebook_conversions_api.log.1

# Search across all log files
grep "Purchase Event" /root/ruxo/logs/facebook_conversions_api.log*
```

---

## 📊 Analyze Logs

### Extract All Payloads to JSON File
```bash
# Extract all request payloads
grep -A 50 "Request Payload:" /root/ruxo/logs/facebook_conversions_api.log > /root/ruxo/fb_requests.txt

# Extract all responses
grep -A 10 "Response Body:" /root/ruxo/logs/facebook_conversions_api.log > /root/ruxo/fb_responses.txt
```

### Generate Statistics
```bash
# Total events by type
grep "OUTGOING REQUEST" /root/ruxo/logs/facebook_conversions_api.log | cut -d'-' -f2 | sort | uniq -c

# Success rate
total=$(grep "OUTGOING REQUEST" /root/ruxo/logs/facebook_conversions_api.log | wc -l)
successful=$(grep '"events_received": 1' /root/ruxo/logs/facebook_conversions_api.log | wc -l)
echo "Success rate: $successful / $total"
```

### Monitor File Size
```bash
# Check current file size
du -h /root/ruxo/logs/facebook_conversions_api.log

# Monitor growth
watch -n 5 'du -h /root/ruxo/logs/facebook_conversions_api.log*'
```

---

## 🎯 Quick Commands

```bash
# Watch live (best for monitoring)
tail -f /root/ruxo/logs/facebook_conversions_api.log

# View last 50 lines
tail -n 50 /root/ruxo/logs/facebook_conversions_api.log

# View last event
tail -n 100 /root/ruxo/logs/facebook_conversions_api.log | grep -A 50 "OUTGOING REQUEST" | tail -50

# Copy log to desktop for analysis
cp /root/ruxo/logs/facebook_conversions_api.log ~/facebook_events_$(date +%Y%m%d).log

# Clear old logs (be careful!)
# rm /root/ruxo/logs/facebook_conversions_api.log.*
```

---

## 🔒 Security Notes

- ✅ Access token is **masked** in logs (`EAALqz...xyz`)
- ✅ Email is **hashed** (SHA-256, 64 char hex)
- ✅ Names are **hashed** (SHA-256)
- ✅ IP addresses are **NOT hashed** (required by Facebook)
- ✅ File permissions: Only root can read (600)

### Set Secure Permissions
```bash
chmod 600 /root/ruxo/logs/facebook_conversions_api.log
chown root:root /root/ruxo/logs/facebook_conversions_api.log
```

---

## 🚨 Troubleshooting

### Log File Not Created
```bash
# Check if directory exists
ls -la /root/ruxo/logs/

# If not, create it
mkdir -p /root/ruxo/logs

# Restart backend
sudo systemctl restart ruxo-backend

# Trigger a test event (visit pricing page)
```

### File Growing Too Large
```bash
# Check size
du -h /root/ruxo/logs/facebook_conversions_api.log*

# Manual rotation if needed
mv /root/ruxo/logs/facebook_conversions_api.log /root/ruxo/logs/facebook_conversions_api.log.manual.$(date +%Y%m%d)
sudo systemctl restart ruxo-backend
```

### Want More Detail
The log already includes everything! But if you need even more:
- Request/Response headers: Already included ✅
- Full JSON payloads: Already included ✅
- Timestamps: Already included ✅

---

## 📈 Integration with Monitoring

### Send to External Log Service
```bash
# Example: Send to remote syslog
tail -f /root/ruxo/logs/facebook_conversions_api.log | nc your-log-server.com 514

# Example: Send to S3 daily
aws s3 cp /root/ruxo/logs/facebook_conversions_api.log s3://your-bucket/logs/$(date +%Y-%m-%d)/
```

### Alert on Errors
```bash
# Monitor for errors and send email
tail -f /root/ruxo/logs/facebook_conversions_api.log | grep --line-buffered "error" | while read line; do
    echo "$line" | mail -s "Facebook API Error" admin@example.com
done
```

---

## ✅ Summary

| Feature | Value |
|---------|-------|
| **Log File** | `/root/ruxo/logs/facebook_conversions_api.log` |
| **Max Size** | 50 MB (auto-rotates) |
| **Retention** | 5 backup files (250 MB total) |
| **Format** | Structured text with JSON payloads |
| **Contents** | Complete requests & responses |
| **Security** | Access tokens masked, PII hashed |
| **Created** | Automatically on first event |

**Status**: ✅ Active and logging  
**Location**: `/root/ruxo/logs/`  
**Watch Live**: `tail -f /root/ruxo/logs/facebook_conversions_api.log`

