# Testing Facebook Conversions API Tracking

This guide explains how to test all Facebook conversion events.

## Quick Test Commands

### 1. Test CompleteRegistration (Manual Signup)

```bash
# Using the test script
cd /root/ruxo/backend
python scripts/test_conversion_tracking.py --test complete-registration

# Or manually via curl
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!",
    "display_name": "Test User"
  }'
```

**Expected logs:**
```
Triggered CompleteRegistration event tracking for signup - user {id}
Successfully sent CompleteRegistration event to Facebook Conversions API. Events received: 1
```

### 2. Test ViewContent (Page Views)

```bash
# Using the test script
python scripts/test_conversion_tracking.py --test view-content --url /signup

# Or manually via curl
curl -X POST "http://localhost:8000/api/v1/billing/track-view-content?url=https://ruxo.ai/signup" \
  -H "Content-Type: application/json"
```

**Expected logs:**
```
ViewContent tracking request - URL: https://ruxo.ai/signup, User: anonymous
Triggered ViewContent event tracking for URL: https://ruxo.ai/signup
Successfully sent ViewContent event to Facebook Conversions API. Events received: 1
```

### 3. Test InitiateCheckout

```bash
# Using the test script
python scripts/test_conversion_tracking.py --test initiate-checkout

# Or manually via curl
curl -X POST http://localhost:8000/api/v1/billing/track-initiate-checkout \
  -H "Content-Type: application/json"
```

**Expected logs:**
```
Successfully sent InitiateCheckout event to Facebook Conversions API. Events received: 1
```

### 4. Test Purchase

```bash
# Using the test script (requires JWT token)
python scripts/test_conversion_tracking.py --test purchase --value 29.99

# Or manually via curl (requires JWT token)
curl -X POST http://localhost:8000/api/v1/billing/test-purchase \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Expected logs:**
```
Successfully sent Purchase event to Facebook Conversions API. Events received: 1
```

## Monitoring Logs

### Watch all conversion events in real-time:

```bash
sudo journalctl -u ruxo-backend -f | grep -i "facebook\|complete\|viewcontent\|initiate\|purchase"
```

### Watch specific events:

```bash
# CompleteRegistration
sudo journalctl -u ruxo-backend -f | grep -i "complete\|registration"

# ViewContent
sudo journalctl -u ruxo-backend -f | grep -i "viewcontent"

# InitiateCheckout
sudo journalctl -u ruxo-backend -f | grep -i "initiate"

# Purchase
sudo journalctl -u ruxo-backend -f | grep -i "purchase"
```

## Testing Frontend Pages

### 1. Test Signup Page ViewContent

1. Open browser and navigate to: `https://ruxo.ai/signup`
2. Open browser console (F12)
3. Look for: `Tracking ViewContent: /billing/track-view-content?url=...`
4. Check backend logs for ViewContent event

### 2. Test Login Page ViewContent

1. Navigate to: `https://ruxo.ai/login`
2. Check browser console and backend logs

### 3. Test Complete Registration Flow

1. Navigate to: `https://ruxo.ai/signup`
2. Click "Continue with Email"
3. Fill in email and display name
4. Fill in password
5. Submit form
6. Check backend logs for:
   - ViewContent (page views)
   - CompleteRegistration (on successful signup)

### 4. Test Login Flow

1. Navigate to: `https://ruxo.ai/login`
2. Click "Continue with Email"
3. Enter credentials and login
4. Check backend logs for:
   - ViewContent (page views)
   - ViewContent (on successful login)

## Testing All Events at Once

```bash
cd /root/ruxo/backend
python scripts/test_conversion_tracking.py --test all
```

## Verification Checklist

- [ ] CompleteRegistration fires on manual email/password signup (no verification)
- [ ] CompleteRegistration does NOT fire on OAuth signup
- [ ] CompleteRegistration does NOT fire on email signup with verification
- [ ] ViewContent fires when viewing /signup page
- [ ] ViewContent fires when viewing /login page
- [ ] ViewContent fires when viewing /signup-email page
- [ ] ViewContent fires when viewing /signup-password page
- [ ] ViewContent fires when viewing /login-email page
- [ ] ViewContent fires on successful signup (backend)
- [ ] ViewContent fires on successful login (backend)
- [ ] InitiateCheckout fires when viewing /upgrade page (with plans loaded)
- [ ] InitiateCheckout does NOT fire on login
- [ ] Purchase fires when Stripe checkout completes

## Troubleshooting

### No events in logs?

1. Check if backend is running: `sudo systemctl status ruxo-backend`
2. Check for errors: `sudo journalctl -u ruxo-backend -n 50 | grep -i error`
3. Verify Facebook credentials in `.env`:
   - `FACEBOOK_PIXEL_ID`
   - `FACEBOOK_ACCESS_TOKEN`

### Events not reaching Facebook?

1. Check Facebook API responses in logs
2. Verify Pixel ID matches frontend and backend
3. Check access token permissions in Facebook Business Manager
4. Verify events in Facebook Events Manager (may take a few minutes)

### Frontend not tracking?

1. Check browser console for errors
2. Verify `NEXT_PUBLIC_API_V1_URL` is set correctly
3. Check network tab to see if requests are being sent
4. Verify frontend is deployed/restarted

## Facebook Events Manager

After testing, verify events in Facebook Events Manager:
1. Go to Facebook Business Manager
2. Navigate to Events Manager
3. Select your Pixel
4. Check "Test Events" tab for real-time events
5. Check "Overview" tab for aggregated data (may take time to appear)

