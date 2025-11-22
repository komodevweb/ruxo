# Testing Monthly Credit Reset for Yearly Plans

This guide explains how to verify that the scheduler correctly resets credits monthly for yearly subscriptions.

## Overview

The scheduler runs **daily at 2:00 AM** and checks all active subscriptions:
- **Yearly plans**: Resets credits every month (if 1+ month has passed since last reset)
- **Monthly plans**: Resets when billing period changes (handled by Stripe webhooks, scheduler is fallback)

## Quick Test Methods

### Method 1: Admin API Endpoint (Recommended)

1. **Start your backend server**
2. **Call the admin endpoint** (requires admin authentication):
   ```bash
   curl -X POST http://localhost:8000/api/v1/admin/test/credit-reset \
     -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
   ```
3. **Check the logs** - you'll see detailed output about which subscriptions were checked and reset

### Method 2: Test Script

1. **Run the test script**:
   ```bash
   cd backend
   python scripts/test_credit_reset.py
   ```
2. **Choose an option**:
   - Option 1: Run actual credit reset (checks and resets if needed)
   - Option 2: Simulate 30 days passing (modify `last_credit_reset` for yearly plans)
   - Option 3: Both (simulate then reset)

### Method 3: Manual Database Modification

1. **Connect to your database**
2. **Find a yearly subscription**:
   ```sql
   SELECT s.id, s.user_id, s.last_credit_reset, p.name, p.interval
   FROM subscriptions s
   JOIN plans p ON s.plan_id = p.id
   WHERE s.status = 'active' AND p.interval = 'year';
   ```
3. **Set `last_credit_reset` to 31 days ago**:
   ```sql
   UPDATE subscriptions
   SET last_credit_reset = NOW() - INTERVAL '31 days'
   WHERE id = 'YOUR_SUBSCRIPTION_ID';
   ```
4. **Trigger the reset** (use Method 1 or 2)

## Verifying It Works

### Check 1: Yearly Plans Reset Monthly

1. Create or find a yearly subscription
2. Set `last_credit_reset` to 31+ days ago
3. Run the reset task
4. **Expected**: Credits reset to plan amount, `last_credit_reset` updated to now

### Check 2: Monthly Plans Don't Reset (Unless Billing Period Changed)

1. Create or find a monthly subscription
2. Set `last_credit_reset` to 31+ days ago (but keep `current_period_start` recent)
3. Run the reset task
4. **Expected**: Credits NOT reset (because billing period hasn't changed)

### Check 3: Yearly Plans Don't Reset Too Early

1. Create or find a yearly subscription
2. Set `last_credit_reset` to 20 days ago (less than 1 month)
3. Run the reset task
4. **Expected**: Credits NOT reset (not yet 1 month)

## Detailed Logs

The scheduler provides detailed logging:

```
============================================================
Starting scheduled credit reset task...
============================================================
Found 2 active subscription(s) to check
Checking subscription abc-123 (Pro Yearly, year)...
  Last reset: 2024-10-21 00:00:00
  Current balance: 50 credits
  ✅ YEARLY PLAN: Credits reset monthly!
  Last reset: 2024-10-21 00:00:00 → 2024-11-21 00:00:00
  Balance: 50 → 100 credits
  Plan credits/month: 100
  ✅ Balance correctly set to plan amount!
Checking subscription def-456 (Pro Monthly, month)...
  Last reset: 2024-10-21 00:00:00
  Current balance: 50 credits
  ⏳ No reset needed (not yet time for this subscription)
============================================================
Credit reset task completed:
  Total subscriptions checked: 2
  Total resets: 1
  Yearly plan resets: 1
  Monthly plan resets: 0
============================================================
```

## Simulating 30-Day Cycle

### Step-by-Step

1. **Create a yearly subscription** (or use existing)
2. **Check current state**:
   ```sql
   SELECT 
     s.id,
     s.user_id,
     s.last_credit_reset,
     p.name,
     p.interval,
     p.credits_per_month
   FROM subscriptions s
   JOIN plans p ON s.plan_id = p.id
   WHERE s.status = 'active' AND p.interval = 'year';
   ```

3. **Simulate 30 days passing**:
   ```sql
   UPDATE subscriptions
   SET last_credit_reset = NOW() - INTERVAL '31 days'
   WHERE id = 'YOUR_SUBSCRIPTION_ID';
   ```

4. **Check user's current balance**:
   ```sql
   SELECT balance_credits FROM wallets WHERE user_id = 'YOUR_USER_ID';
   ```

5. **Run the reset task** (Method 1 or 2)

6. **Verify**:
   - `last_credit_reset` updated to current time
   - `balance_credits` set to `plan.credits_per_month`
   - Logs show "✅ YEARLY PLAN: Credits reset monthly!"

7. **Repeat** - Set `last_credit_reset` to 31 days ago again and run reset to simulate next month

## Troubleshooting

### Issue: "No reset needed" for yearly plan

**Cause**: Less than 1 month has passed since last reset

**Solution**: Set `last_credit_reset` to 31+ days ago

### Issue: "Webhook secret not configured"

**Cause**: The security check is blocking the reset

**Solution**: 
- For production: Set `STRIPE_WEBHOOK_SECRET` in `.env`
- For testing: The scheduler bypasses this check (it's only for webhook handlers)

### Issue: Credits not resetting

**Check**:
1. Is the subscription `status = 'active'`?
2. Does the subscription have a `plan_id`?
3. Does the plan have `credits_per_month` set?
4. Is `last_credit_reset` set (not NULL)?
5. For yearly: Has 1+ month passed since `last_credit_reset`?
6. Check logs for errors

## Production Verification

In production, the scheduler runs automatically at 2:00 AM daily. To verify:

1. **Check logs** the next morning for scheduler activity
2. **Monitor** subscription `last_credit_reset` dates - they should update monthly for yearly plans
3. **Monitor** user credit balances - they should reset to plan amount monthly for yearly plans

## Notes

- **Monthly plans**: Credits reset when Stripe sends `invoice.payment_succeeded` webhook (billing period changes)
- **Yearly plans**: Credits reset monthly via scheduler (even though billing period is yearly)
- **Security**: The scheduler is an internal, trusted component, so it bypasses webhook secret checks
- **Idempotent**: Safe to run multiple times - it only resets if conditions are met


