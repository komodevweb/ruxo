# Ruxo Backend - Quick Start Guide

## Prerequisites

- Python 3.11 or higher
- PostgreSQL database (via Supabase)
- Supabase account and project
- Stripe account (for payments)

## Step-by-Step Setup

### 1. Navigate to Backend Directory

```bash
cd backend
```

### 2. Create Virtual Environment (Recommended)

**Windows:**
```powershell
python -m venv venv
venv\Scripts\activate
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Generate Security Keys

```bash
python scripts/generate_secrets.py
```

Copy the generated keys (you'll need them for the `.env` file).

### 5. Configure Environment Variables

**Copy the example file:**
```bash
# Windows PowerShell
Copy-Item env.example .env

# Mac/Linux
cp env.example .env
```

**Edit `.env` and fill in:**

```env
# Database (Your Supabase connection string)
DATABASE_URL="postgresql+asyncpg://postgres:YOUR_PASSWORD@db.xxxxx.supabase.co:5432/postgres"

# Supabase
SUPABASE_URL="https://xxxxx.supabase.co"
SUPABASE_KEY="your-anon-key"
SUPABASE_JWT_SECRET="your-jwt-secret"  # Get from Supabase Dashboard > Settings > API

# Stripe
STRIPE_API_KEY="sk_test_..."
STRIPE_WEBHOOK_SECRET="whsec_..."

# Security (from generate_secrets.py output)
SECRET_KEY="your-generated-secret-key"
API_KEY_ENCRYPTION_KEY="your-generated-encryption-key"
SESSION_SECRET="your-generated-session-secret"

# Admin
ADMIN_EMAILS="admin@ruxo.ai"
SUPER_ADMIN_EMAIL="admin@ruxo.ai"

# Frontend
FRONTEND_URL="http://localhost:3000"
BACKEND_BASE_URL="http://localhost:8000"
```

### 6. Run Database Migrations

```bash
# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

### 7. Start the Server

**Development (with auto-reload):**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Production:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The server will start at: **http://localhost:8000**

## Verify It's Working

1. **Health Check:**
   ```bash
   curl http://localhost:8000/health
   ```
   Should return: `{"status":"ok","version":"0.1.0"}`

2. **API Documentation:**
   - Swagger UI: http://localhost:8000/api/v1/docs
   - ReDoc: http://localhost:8000/api/v1/redoc

## Common Issues

### Issue: Module not found
**Solution:** Make sure virtual environment is activated and dependencies are installed:
```bash
pip install -r requirements.txt
```

### Issue: Database connection error
**Solution:** Check your `DATABASE_URL` in `.env` file. Make sure:
- Password is correct
- Database is accessible
- Connection string uses `postgresql+asyncpg://` (not `postgresql://`)

### Issue: Missing environment variables
**Solution:** Make sure all required variables in `env.example` are set in your `.env` file.

### Issue: Migration errors
**Solution:** 
```bash
# Check current migration status
alembic current

# If needed, reset (WARNING: This will drop all tables)
alembic downgrade base
alembic upgrade head
```

## API Endpoints

Once running, you can access:

- `GET /health` - Health check
- `GET /api/v1/docs` - Swagger documentation
- `GET /api/v1/auth/me` - Get current user (requires auth)
- `POST /api/v1/billing/create-checkout-session` - Create Stripe checkout
- `GET /api/v1/credits/me` - Get credit balance
- `POST /api/v1/renders/` - Create render job

## Development Tips

- Use `--reload` flag for auto-restart on code changes
- Check logs in terminal for errors
- Use Swagger UI at `/api/v1/docs` to test endpoints
- All endpoints require Supabase JWT token in `Authorization: Bearer <token>` header

## Next Steps

1. Seed initial data (plans, etc.) in your database
2. Test authentication flow
3. Configure Stripe webhooks
4. Set up monitoring/logging

