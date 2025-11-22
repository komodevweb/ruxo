# Stripe Integration Setup Guide

## Overview

The billing system is now fully integrated with Stripe and supports:
- **Monthly credit resets**: Credits reset to plan amount each billing period
- **Yearly subscriptions**: Same monthly credits, paid yearly
- **Automatic credit management**: Credits reset when payment succeeds

## Plans Configuration

### Monthly Plans
1. **Starter Monthly**: $20/month - 200 credits/month
2. **Pro Monthly**: $39/month - 400 credits/month  
3. **Creator Monthly**: $99/month - 1000 credits/month
4. **Ultimate Monthly**: $200/month - 2000 credits/month

### Yearly Plans
1. **Starter Yearly**: $200/year - 200 credits/month
2. **Pro Yearly**: $390/year - 400 credits/month
3. **Creator Yearly**: $990/year - 1000 credits/month
4. **Ultimate Yearly**: $2000/year - 2000 credits/month

## Setup Steps

### 1. Configure Stripe Keys

Add to `backend/.env`:
```env
STRIPE_API_KEY="sk_test_YOUR_SECRET_KEY"
STRIPE_WEBHOOK_SECRET="whsec_YOUR_WEBHOOK_SECRET"
```

### 2. Seed Plans in Stripe and Database

Run the seeding script to create all plans:
```bash
cd backend
python scripts/seed_plans.py
```

This will:
- Create products in Stripe
- Create prices in Stripe
- Create Plan records in your database

### 3. Set Up Webhook Endpoint

In Stripe Dashboard → Webhooks:
- Add endpoint: `https://your-domain.com/api/v1/webhooks/stripe`
- Select events:
  - `checkout.session.completed`
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `invoice.payment_succeeded`
  - `invoice.payment_failed`

### 4. Set Up Monthly Credit Reset (Optional)

For automatic monthly resets, set up a cron job or scheduled task:
```bash
# Run daily to check for subscriptions needing credit resets
python backend/scripts/reset_monthly_credits.py
```

Or use the webhook-based reset (recommended) - credits reset automatically when `invoice.payment_succeeded` is received.

## How It Works

### Credit Reset Logic

1. **On Subscription Start**: User gets plan's monthly credits
2. **Monthly Renewal**: 
   - Credits reset to plan amount (not added)
   - If user spent credits, balance goes to plan amount
   - If user didn't spend, balance was already at plan amount
3. **Yearly Plans**: Same monthly credits, but paid yearly

### Webhook Flow

1. User subscribes → `checkout.session.completed`
2. Subscription created → `customer.subscription.created`
3. Credits reset to plan amount
4. Monthly renewal → `invoice.payment_succeeded`
5. Credits reset again to plan amount

## API Endpoints

- `GET /api/v1/billing/plans` - List all available plans
- `POST /api/v1/billing/create-checkout-session` - Create Stripe checkout
- `POST /api/v1/billing/create-portal-session` - Manage subscription
- `POST /api/v1/webhooks/stripe` - Stripe webhook handler

## Database Changes Needed

You'll need to run a migration to:
1. Rename `credits_provided` to `credits_per_month` in `plans` table
2. Add `last_credit_reset` column to `subscriptions` table
3. Add `plan_id` foreign key to `subscriptions` table

Run Alembic migration after updating models.

