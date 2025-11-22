# Scripts Directory

This directory contains utility scripts for the Ruxo backend.

## Available Scripts

### `test_scheduler.py`

Test the scheduler task manually (without waiting for 2:00 AM).

**Usage:**
```bash
# From the backend directory
python scripts/test_scheduler.py
```

This will trigger the `reset_monthly_credits_task` that normally runs daily at 2:00 AM.

### `test_credit_reset.py`

Interactive script to test credit reset logic with simulation options.

**Usage:**
```bash
python scripts/test_credit_reset.py
```

Options:
1. Run actual credit reset (checks and resets if needed)
2. Simulate 30 days passing (modify last_credit_reset for yearly plans)
3. Both (simulate then reset)
4. Exit

### `reset_monthly_credits.py`

Standalone script to manually trigger credit resets (can be run via cron).

**Usage:**
```bash
python scripts/reset_monthly_credits.py
```

### `generate_secrets.py`

Generates secure random keys for environment variables.

**Usage:**
```bash
python scripts/generate_secrets.py
```

This will generate:
- `SECRET_KEY` - For API key hashing and session tokens
- `API_KEY_ENCRYPTION_KEY` - For encrypting sensitive data
- `SESSION_SECRET` - For session management

Copy the output to your `.env` file.

