# Facebook Conversion Tracking Setup

## 📊 Event Flow Overview

This document describes how Facebook conversion events are tracked in the Ruxo application.

## 🎯 Conversion Events

### 1. **CompleteRegistration** 
Fires immediately when user registers, regardless of email verification status:

#### Scenario A: Manual Signup (Email/Password)
- **When**: User completes signup form with email/password
- **Fires**: Immediately after form submission
- **Note**: Fires even if email verification is required

#### Scenario B: OAuth Signup
- **When**: User completes OAuth signup (Google, Microsoft, Apple)
- **Fires**: Immediately after OAuth exchange
- **Note**: OAuth providers pre-verify emails

### 2. **InitiateCheckout**
- **When**: User clicks "Select Plan" button on pricing page
- **Fires**: On button click (NOT on page view)
- **Parameters**: Full user data + plan context

### 3. **Purchase**
- **When**: Subscription payment succeeds
- **Trigger**: Stripe webhook
- **Parameters**: Purchase value, currency, transaction ID

## 📤 Parameters Sent to Meta

All events include comprehensive parameters for optimal matching:

```python
✅ Event Metadata:
   • event_name: Event type (Lead, CompleteRegistration, etc.)
   • event_time: Unix timestamp
   • action_source: "website"
   • event_source_url: Page URL where event occurred
   • event_id: Unique ID for deduplication

✅ User Data (PII is SHA-256 hashed):
   • em: Email address (hashed)
   • fn: First name (hashed)
   • ln: Last name (hashed)
   • external_id: User UUID (not hashed)
   • client_ip_address: User's IP
   • client_user_agent: Browser user agent
   • fbp: Facebook browser ID (_fbp cookie)
   • fbc: Facebook click ID (_fbc cookie)

✅ Custom Data (for Purchase):
   • currency: "USD"
   • value: Purchase amount
```

## 🔧 Supabase Webhook Setup (OPTIONAL - Not Currently Used)

**Note**: The webhook endpoint exists at `/api/v1/webhooks/supabase-auth` but is NOT required since CompleteRegistration fires immediately on signup.

If you want to track additional events on email verification in the future, you can configure it, but it's not needed for the current setup.

## 🧪 Testing

Use the test script to verify tracking:

```bash
cd /root/ruxo/backend

# Test manual signup (will fire Lead)
python scripts/test_conversion_tracking.py --test complete-registration

# Test InitiateCheckout
python scripts/test_conversion_tracking.py --test initiate-checkout

# Test Purchase
python scripts/test_conversion_tracking.py --test purchase --value 29.99
```

## 📝 Event Flow Examples

### Example 1: Manual Signup with Email Verification
```
User Action                     → Meta Event
────────────────────────────────────────────────
1. Fill signup form             → (no event)
2. Submit form                  → CompleteRegistration ✅
3. Check email                  → (no event)
4. Click verification link      → (no event)
5. Login                        → (no event)
```

### Example 2: OAuth Signup (Google)
```
User Action                     → Meta Event
────────────────────────────────────────────────
1. Click "Sign in with Google"  → (no event)
2. Authorize on Google          → (no event)
3. Return to app                → CompleteRegistration ✅
4. Auto-logged in               → (no event)
```

### Example 3: Pricing → Checkout → Purchase
```
User Action                     → Meta Event
────────────────────────────────────────────────
1. View pricing page            → (no event)
2. Click "Select Plan"          → InitiateCheckout ✅
3. Fill payment info            → (no event)
4. Submit payment               → (no event)
5. Payment succeeds (webhook)   → Purchase ✅
```

## 🔍 Debugging

### Check Backend Logs
```bash
# All conversion events
sudo journalctl -u ruxo-backend -f | grep "🎯"

# CompleteRegistration events (signup)
sudo journalctl -u ruxo-backend -f | grep "CompleteRegistration"

# InitiateCheckout events (pricing page)
sudo journalctl -u ruxo-backend -f | grep "InitiateCheckout"

# Purchase events (stripe webhook)
sudo journalctl -u ruxo-backend -f | grep "Purchase"
```

### Check Frontend Console
Open browser DevTools (F12) → Console:
- Look for 🔘 (button clicks)
- Look for 🎯 (tracking calls)
- Look for ✅ (success) or ❌ (blocked) events

### Verify in Meta Events Manager
1. Go to **Meta Events Manager**
2. Select your Pixel
3. Click **Test Events**
4. Perform actions on your site
5. Verify events appear with all parameters

## ⚙️ Configuration

### Environment Variables
Ensure these are set in `.env`:

```bash
# Facebook/Meta
FACEBOOK_PIXEL_ID=your_pixel_id
FACEBOOK_ACCESS_TOKEN=your_access_token

# Frontend URL (for event_source_url)
FRONTEND_URL=https://ruxo.ai
```

### Event IDs for Deduplication
Event IDs are automatically generated in format:
- Lead: `lead_{user_id}_{timestamp}`
- CompleteRegistration: `registration_{user_id}_{timestamp}`

This prevents duplicate counting if you also use Meta Pixel on frontend.

## ✅ Best Practices

1. **Don't fire CompleteRegistration twice** - Use Lead for unverified, CompleteRegistration for verified
2. **Include event_id** - Prevents duplicate counting with Pixel
3. **Send all user data** - Better matching = better attribution
4. **Hash PII properly** - Email/names must be SHA-256 hashed (done automatically)
5. **Use accurate event_source_url** - Helps Meta attribute conversions correctly

## 🚨 Common Issues

### Issue: CompleteRegistration not firing after email verification
**Solution**: Check Supabase webhook is configured and pointing to correct URL

### Issue: Duplicate events in Meta
**Solution**: Ensure event_id is being sent and is identical between Pixel and CAPI

### Issue: Poor event match quality
**Solution**: Ensure fbp, fbc cookies and client IP are being sent

### Issue: Events firing on page load instead of button click
**Solution**: Check button onClick handlers pass the event object properly

## 📚 References

- [Meta Conversions API Documentation](https://developers.facebook.com/docs/marketing-api/conversions-api)
- [Event Deduplication](https://developers.facebook.com/docs/marketing-api/conversions-api/deduplicate-pixel-and-server-events)
- [User Data Parameters](https://developers.facebook.com/docs/marketing-api/conversions-api/parameters/customer-information-parameters)

