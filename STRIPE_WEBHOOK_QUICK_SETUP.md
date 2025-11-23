# Quick Guide: Add Stripe Webhook

## Your Webhook URL
```
https://api.ruxo.ai/api/v1/webhooks/stripe
```

## Step-by-Step Instructions

### 1. Open Stripe Dashboard
- Go to: https://dashboard.stripe.com
- Make sure you're logged into the **correct Stripe account** (production account)

### 2. Navigate to Webhooks
1. Click **"Developers"** in the left sidebar (at the bottom)
2. Click **"Webhooks"** in the submenu
3. You'll see a list of existing webhooks (if any)

### 3. Add New Webhook Endpoint
1. Click the **"+ Add endpoint"** button (top right)
2. A form will appear with these fields:

### 4. Fill in the Webhook Form

**Endpoint URL:**
```
https://api.ruxo.ai/api/v1/webhooks/stripe
```
Paste this exact URL into the "Endpoint URL" field.

**Description (optional):**
```
Ruxo Production - Subscriptions & Payments
```

**Events to send:**
- Click **"Select events"** (don't use "Send all events")
- Check these specific events:
  - ✅ `checkout.session.completed`
  - ✅ `customer.subscription.created`
  - ✅ `customer.subscription.updated`
  - ✅ `customer.subscription.deleted`
  - ✅ `invoice.payment_succeeded`
  - ✅ `invoice.payment_failed`
  - ✅ `charge.refunded`

### 5. Save the Webhook
1. Click **"Add endpoint"** button
2. Stripe will create the webhook and show you the details page

### 6. Get Your Webhook Signing Secret
1. On the webhook details page, find the **"Signing secret"** section
2. Click **"Reveal"** or **"Click to reveal"** button
3. Copy the secret (it starts with `whsec_...`)
4. It will look like: `whsec_55fe9d6bccd5d76bcb853123de8a9d7dbc653c20a923cd34f102e4b3c4b563af`

### 7. Update Your Backend (If Secret Changed)
If you got a NEW signing secret from Stripe:

1. Edit your backend `.env` file:
   ```bash
   sudo nano /root/ruxo/backend/.env
   ```

2. Find this line:
   ```
   STRIPE_WEBHOOK_SECRET="whsec_..."
   ```

3. Replace the value with your NEW secret from Stripe

4. Save and exit (Ctrl+X, then Y, then Enter)

5. Restart the backend:
   ```bash
   sudo systemctl restart ruxo-backend
   ```

### 8. Test the Webhook
1. In Stripe Dashboard, go back to your webhook endpoint
2. Click **"Send test webhook"** button
3. Select an event type (e.g., `checkout.session.completed`)
4. Click **"Send test webhook"**
5. Check the **"Recent deliveries"** tab:
   - ✅ Green checkmark = Success
   - ❌ Red X = Failed (check error message)

## Visual Guide

```
Stripe Dashboard
├── Developers (left sidebar)
│   └── Webhooks
│       └── + Add endpoint
│           ├── Endpoint URL: https://api.ruxo.ai/api/v1/webhooks/stripe
│           ├── Description: (optional)
│           └── Events to send: Select events
│               ├── ✅ checkout.session.completed
│               ├── ✅ customer.subscription.created
│               ├── ✅ customer.subscription.updated
│               ├── ✅ customer.subscription.deleted
│               ├── ✅ invoice.payment_succeeded
│               ├── ✅ invoice.payment_failed
│               └── ✅ charge.refunded
│           └── [Add endpoint button]
```

## Verify It's Working

After setup, you can verify:

1. **Check webhook is active:**
   - In Stripe Dashboard → Webhooks
   - Your endpoint should show status: **"Enabled"** ✅

2. **Check recent deliveries:**
   - Click on your webhook endpoint
   - Go to **"Recent deliveries"** tab
   - You should see webhook attempts (even if some fail initially)

3. **Test with a real checkout:**
   - Go to your site: https://ruxo.ai/upgrade
   - Complete a test subscription
   - Check Stripe Dashboard → Webhooks → Recent deliveries
   - You should see `checkout.session.completed` event

## Troubleshooting

### Webhook shows "Failed" in Stripe
1. Check backend logs:
   ```bash
   sudo journalctl -u ruxo-backend -n 50 --no-pager | grep -i webhook
   ```

2. Common issues:
   - **Signature verification failed**: Webhook secret doesn't match
   - **500 error**: Check backend logs for database/connection issues
   - **404 error**: Webhook URL is wrong

### Webhook Secret Doesn't Match
If you see "Signature verification failed":
1. Get the signing secret from Stripe Dashboard (webhook details page)
2. Update `/root/ruxo/backend/.env`:
   ```bash
   STRIPE_WEBHOOK_SECRET="whsec_YOUR_SECRET_FROM_STRIPE"
   ```
3. Restart backend:
   ```bash
   sudo systemctl restart ruxo-backend
   ```

### Webhook Not Receiving Events
1. Verify webhook is **Enabled** in Stripe Dashboard
2. Check the webhook URL is exactly: `https://api.ruxo.ai/api/v1/webhooks/stripe`
3. Make sure SSL is working: `curl https://api.ruxo.ai/api/v1/webhooks/stripe` (should return 400, not SSL error)
4. Check backend is running: `sudo systemctl status ruxo-backend`

## Current Configuration Status

✅ **Webhook URL**: `https://api.ruxo.ai/api/v1/webhooks/stripe`  
✅ **Backend Endpoint**: Configured and ready  
✅ **Webhook Secret**: Already in `.env` file  
⏳ **Action Required**: Add webhook endpoint in Stripe Dashboard

## Quick Test Command

Test if your webhook endpoint is accessible (should return 400 - that's expected without proper signature):

```bash
curl -X POST https://api.ruxo.ai/api/v1/webhooks/stripe
```

Expected response:
```json
{"detail":"Missing stripe-signature header"}
```

This confirms the endpoint is working! ✅

