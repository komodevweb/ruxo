# Ruxo Backend - Security Setup Guide

## Quick Start

1. **Generate Security Keys**
   ```bash
   cd backend
   python scripts/generate_secrets.py
   ```
   Copy the generated keys to your `.env` file.

2. **Configure Environment Variables**
   - Copy `env.example` to `.env`
   - Fill in all required values (see below)

3. **Set Up Database**
   ```bash
   alembic revision --autogenerate -m "Initial migration"
   alembic upgrade head
   ```

4. **Run the Server**
   ```bash
   uvicorn app.main:app --reload
   ```

## Required Environment Variables

### Database
- `DATABASE_URL` - PostgreSQL connection string with asyncpg driver

### Supabase
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Supabase anon/public key
- `SUPABASE_JWT_SECRET` - JWT secret from Supabase dashboard (Settings > API > JWT Secret)

### Stripe
- `STRIPE_API_KEY` - Stripe API key (starts with `sk_test_` or `sk_live_`)
- `STRIPE_WEBHOOK_SECRET` - Webhook signing secret (starts with `whsec_`)

### Security (Generate using `scripts/generate_secrets.py`)
- `SECRET_KEY` - 32-byte hex string for API key hashing
- `API_KEY_ENCRYPTION_KEY` - Base64-encoded 32-byte key for encryption
- `SESSION_SECRET` - 32-byte hex string for session management

### Admin
- `ADMIN_EMAILS` - Comma-separated list of admin email addresses
- `SUPER_ADMIN_EMAIL` - Primary admin email

### Frontend
- `FRONTEND_URL` - Your frontend URL (e.g., `http://localhost:3000`)
- `BACKEND_BASE_URL` - Your backend URL (e.g., `http://localhost:8000`)

## Optional Security Variables

All optional variables have sensible defaults. See `env.example` for all available options.

## Security Features

- ✅ JWT Authentication (Supabase)
- ✅ Rate Limiting (per IP)
- ✅ Security Headers
- ✅ CORS Protection
- ✅ Webhook Signature Verification
- ✅ API Key Hashing
- ✅ Audit Logging
- ✅ Admin Access Control

See `SECURITY.md` for detailed security documentation.

