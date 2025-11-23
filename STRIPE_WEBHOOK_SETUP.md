# Stripe Webhook Setup Guide

## Your Webhook URL

For your live domain, your Stripe webhook endpoint is:

```
https://api.ruxo.ai/api/v1/webhooks/stripe
```

## Step-by-Step Setup Instructions

### 1. Log into Stripe Dashboard

1. Go to [https://dashboard.stripe.com](https://dashboard.stripe.com)
2. Make sure you're in the **correct Stripe account** (the one you're using for production)

### 2. Navigate to Webhooks

1. In the left sidebar, click on **"Developers"**
2. Click on **"Webhooks"**
3. Click the **"+ Add endpoint"** button

### 3. Configure the Webhook

1. **Endpoint URL**: Enter your webhook URL:
   ```
   https://api.ruxo.ai/api/v1/webhooks/stripe
   ```

2. **Description** (optional): 
   ```
   Ruxo Production Webhook - Handles subscriptions, payments, and refunds
   ```

3. **Events to send**: Select **"Select events"** and choose these events:
   - ✅ `checkout.session.completed` - When a user completes checkout
   - ✅ `customer.subscription.created` - When a subscription is created
   - ✅ `customer.subscription.updated` - When a subscription is updated (plan changes, etc.)
   - ✅ `customer.subscription.deleted` - When a subscription is cancelled
   - ✅ `invoice.payment_succeeded` - When a payment succeeds
   - ✅ `invoice.payment_failed` - When a payment fails
   - ✅ `charge.refunded` - When a charge is refunded (wipes credits and cancels subscription)

4. Click **"Add endpoint"**

### 4. Get Your Webhook Signing Secret

After creating the webhook:

1. Click on the newly created webhook endpoint
2. In the **"Signing secret"** section, click **"Reveal"** or **"Click to reveal"**
3. Copy the signing secret (it starts with `whsec_...`)

### 5. Update Your Backend Configuration

Your webhook secret is already configured in `/root/ruxo/backend/.env`:

```bash
STRIPE_WEBHOOK_SECRET="whsec_55fe9d6bccd5d76bcb853123de8a9d7dbc653c20a923cd34f102e4b3c4b563af"
```

**⚠️ Important**: If you created a NEW webhook endpoint, you'll get a NEW signing secret. You must:
1. Update the `STRIPE_WEBHOOK_SECRET` in `/root/ruxo/backend/.env` with the new secret
2. Restart the backend: `sudo systemctl restart ruxo-backend`

### 6. Test Your Webhook

1. In Stripe Dashboard, go to your webhook endpoint
2. Click **"Send test webhook"**
3. Select an event type (e.g., `checkout.session.completed`)
4. Click **"Send test webhook"**
5. Check the **"Recent deliveries"** section to see if it was successful

### 7. Monitor Webhook Status

You can monitor webhook deliveries in the Stripe Dashboard:
- **Green checkmark** ✅ = Success (200 response)
- **Red X** ❌ = Failed (check the error message)

## What Each Event Does

| Event | What It Does |
|-------|-------------|
| `checkout.session.completed` | Grants subscription and credits when user completes checkout |
| `customer.subscription.created` | Creates subscription record in database |
| `customer.subscription.updated` | Updates subscription (plan changes, status changes) |
| `customer.subscription.deleted` | Cancels subscription and stops credit grants |
| `invoice.payment_succeeded` | Confirms payment and ensures credits are granted |
| `invoice.payment_failed` | Handles failed payments |
| `charge.refunded` | **Wipes user credits and cancels subscription** |

## Troubleshooting

### Webhook Not Receiving Events

1. **Check webhook URL is correct**: Must be `https://api.ruxo.ai/api/v1/webhooks/stripe`
2. **Check SSL certificate**: Your domain must have valid SSL (you're using Cloudflare, so this should be fine)
3. **Check backend is running**: `sudo systemctl status ruxo-backend`
4. **Check webhook secret matches**: Compare the secret in Stripe Dashboard with your `.env` file

### Webhook Returns 400/500 Errors

1. **Check backend logs**: `sudo journalctl -u ruxo-backend -n 100 --no-pager | grep -i webhook`
2. **Verify webhook secret**: Make sure `STRIPE_WEBHOOK_SECRET` in `.env` matches the signing secret in Stripe
3. **Check database connection**: Ensure database is accessible

### Signature Verification Failed

This means the webhook secret doesn't match. Solution:
1. Get the correct signing secret from Stripe Dashboard
2. Update `STRIPE_WEBHOOK_SECRET` in `/root/ruxo/backend/.env`
3. Restart backend: `sudo systemctl restart ruxo-backend`

## Security Notes

- ✅ Webhook signature verification is **enabled** - all webhooks are verified before processing
- ✅ If signature verification fails, **NO credits or subscriptions will be granted**
- ✅ The webhook secret is stored in `.env` and should **never** be committed to Git
- ✅ Webhook endpoint requires valid Stripe signature header

## Quick Commands

```bash
# Check if webhook secret is configured
grep STRIPE_WEBHOOK_SECRET /root/ruxo/backend/.env

# View recent webhook logs
sudo journalctl -u ruxo-backend -n 50 --no-pager | grep -i webhook

# Restart backend after updating webhook secret
sudo systemctl restart ruxo-backend

# Test webhook endpoint (should return 400 without proper signature - this is expected)
curl -X POST https://api.ruxo.ai/api/v1/webhooks/stripe
```

## Current Configuration

- **Webhook URL**: `https://api.ruxo.ai/api/v1/webhooks/stripe`
- **Webhook Secret**: Already configured in `.env`
- **Status**: Ready to activate in Stripe Dashboard

