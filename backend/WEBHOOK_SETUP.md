# How to Listen to Stripe Webhooks

## Backend Setup

Your backend already has a webhook endpoint set up at:
```
POST /api/v1/webhooks/stripe
```

## Step 1: Get Your Webhook Secret

1. Go to [Stripe Dashboard](https://dashboard.stripe.com)
2. Navigate to **Developers** → **Webhooks**
3. Click **Add endpoint** (or use existing one)
4. Set the endpoint URL to: `https://your-domain.com/api/v1/webhooks/stripe`
   - For local development, use a tool like [ngrok](https://ngrok.com) or [Stripe CLI](https://stripe.com/docs/stripe-cli)
5. Select the events you want to listen to (e.g., `checkout.session.completed`, `customer.subscription.updated`)
6. Copy the **Signing secret** (starts with `whsec_...`)

## Step 2: Configure Environment Variables

Add to your `backend/.env`:
```env
STRIPE_WEBHOOK_SECRET="whsec_YOUR_WEBHOOK_SECRET_HERE"
```

## Step 3: Local Development Setup

### Option A: Using Stripe CLI (Recommended)

1. Install Stripe CLI: https://stripe.com/docs/stripe-cli
2. Login: `stripe login`
3. Forward webhooks to your local server:
   ```bash
   stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe
   ```
4. Copy the webhook signing secret from the CLI output
5. Add it to your `.env` file

### Option B: Using ngrok

1. Install ngrok: https://ngrok.com
2. Start your backend server: `uvicorn app.main:app --reload`
3. In another terminal, run:
   ```bash
   ngrok http 8000
   ```
4. Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)
5. In Stripe Dashboard, add webhook endpoint: `https://abc123.ngrok.io/api/v1/webhooks/stripe`
6. Copy the webhook secret to your `.env`

## Step 4: Test Webhook

You can test webhooks using Stripe CLI:
```bash
stripe trigger checkout.session.completed
```

Or manually trigger events from Stripe Dashboard → Webhooks → Test webhook

## Current Webhook Handler

The webhook endpoint (`/api/v1/webhooks/stripe`) currently:
- Verifies the webhook signature
- Handles events via `BillingService.handle_webhook()`
- Returns success status

## Supported Events

Check `backend/app/services/billing_service.py` to see which events are handled. Common events:
- `checkout.session.completed` - Payment successful
- `customer.subscription.created` - New subscription
- `customer.subscription.updated` - Subscription changed
- `customer.subscription.deleted` - Subscription cancelled
- `invoice.payment_succeeded` - Payment received
- `invoice.payment_failed` - Payment failed

## Security Notes

- Always verify webhook signatures (already implemented)
- Use HTTPS in production
- Keep your webhook secret secure
- The endpoint already validates signatures before processing

