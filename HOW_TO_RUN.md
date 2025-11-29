# How to Run Ruxo

This guide provides step-by-step instructions to get Ruxo up and running on your local machine.

> **For Production Deployment**: See [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md) for deploying to `ruxo.ai` and `api.ruxo.ai`

## Prerequisites

Before starting, ensure you have the following installed:

- **Node.js** 20.x or later ([Download](https://nodejs.org/))
- **Python** 3.11 or later ([Download](https://www.python.org/downloads/))
- **PostgreSQL** 14+ (or use Supabase hosted database)
- **Redis** 7.x or later ([Download](https://redis.io/download)) - For caching and rate limiting
- **Git**

### Required Services

You'll need accounts for these services:

1. **Supabase** - For authentication and database ([Sign up](https://supabase.com))
2. **Stripe** - For payment processing ([Sign up](https://stripe.com))
3. **Backblaze B2** - For file storage ([Sign up](https://www.backblaze.com))
4. **WaveSpeed AI** - For AI content generation ([Sign up](https://wavespeed.ai))

---

## Quick Start (5 Steps)

### Step 1: Clone and Navigate

```bash
git clone <repository-url>
cd ruxo
```

### Step 2: Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Generate security keys
python scripts/generate_secrets.py
# Copy the generated keys - you'll need them for .env

# Copy environment template
cp env.example .env

# Edit .env file with your credentials (see Step 3)
```

### Step 3: Configure Backend Environment

Edit `backend/.env` and fill in your credentials:

```env
# Database (from Supabase)
DATABASE_URL="postgresql+asyncpg://postgres:YOUR_PASSWORD@db.xxxxx.supabase.co:5432/postgres"

# Supabase (from Dashboard > Settings > API)
SUPABASE_URL="https://xxxxx.supabase.co"
SUPABASE_JWT_SECRET="your-jwt-secret"

# Stripe (from Dashboard > API Keys)
STRIPE_API_KEY="sk_test_..."
STRIPE_WEBHOOK_SECRET="whsec_..."

# Backblaze B2 (from Dashboard > App Keys)
B2_APPLICATION_KEY_ID="your-key-id"
B2_APPLICATION_KEY="your-application-key"
B2_BUCKET_NAME="ruxo-media"

# WaveSpeed AI (from Dashboard)
WAVESPEED_API_KEY="your-wavespeed-api-key"
WAVESPEED_API_URL="https://api.wavespeed.ai/api/v3"

# Redis (default: localhost)
REDIS_URL="redis://localhost:6379/0"
REDIS_ENABLED=true

# Security (from generate_secrets.py output)
SECRET_KEY="your-generated-secret-key"
API_KEY_ENCRYPTION_KEY="your-generated-encryption-key"

# URLs
FRONTEND_URL="http://localhost:3000"
BACKEND_BASE_URL="http://localhost:8000"
```

### Step 4: Frontend Setup

```bash
cd ../ui

# Install dependencies
npm install

# Copy environment template
cp env.example .env.local

# Edit .env.local (usually just needs the API URL)
```

Edit `ui/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_V1_URL=http://localhost:8000/api/v1
```

### Step 5: Start Redis

**On macOS (using Homebrew):**
```bash
brew install redis
brew services start redis
```

**On Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**On Windows:**
- Download Redis from [Memurai](https://www.memurai.com/get-memurai) or use WSL
- Or use Docker: `docker run -d -p 6379:6379 redis:7-alpine`

**Verify Redis is running:**
```bash
redis-cli ping
# Should return: PONG
```

### Step 6: Database Setup & Run

```bash
# Navigate back to backend
cd ../backend

# Make sure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Run database migrations
alembic upgrade head

# Seed initial data (optional - creates subscription plans)
python scripts/seed_plans.py
```

### Step 7: Start the Application

**Terminal 1 - Start Backend:**
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Start Frontend:**
```bash
cd ui
npm run dev
```

### Step 8: Activate Stripe Local Webhook (Required for Payments)

To receive Stripe webhook events locally (for testing payments, subscriptions, and trial credits), you need to use the Stripe CLI:

**Option A: Using Stripe CLI (Recommended)**

1. **Install Stripe CLI:**
   - Windows: Download from https://github.com/stripe/stripe-cli/releases
   - macOS: `brew install stripe/stripe-cli/stripe`
   - Linux: See https://stripe.com/docs/stripe-cli

2. **Login to Stripe:**
   ```bash
   stripe login
   ```
   This will open your browser to authenticate with Stripe.

3. **Forward webhooks to your local backend:**
   ```bash
   stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe
   ```

4. **Copy the webhook signing secret:**
   The CLI will output something like:
   ```
   > Ready! Your webhook signing secret is whsec_xxxxxxxxxxxxx
   ```
   **Copy this secret!**

5. **Update your `.env` file:**
   Open `backend/.env` and update:
   ```env
   STRIPE_WEBHOOK_SECRET="whsec_xxxxxxxxxxxxx"
   ```
   (Use the secret from step 4)

6. **Restart your backend server** (if it's already running) to load the new webhook secret.

**Option B: Using ngrok (Alternative)**

If you prefer using ngrok instead:

1. **Install ngrok:** https://ngrok.com/download
2. **Start ngrok:**
   ```bash
   ngrok http 8000
   ```
3. **Copy the HTTPS URL** (e.g., `https://abc123.ngrok.io`)
4. **In Stripe Dashboard:**
   - Go to https://dashboard.stripe.com/webhooks
   - Click "Add endpoint"
   - Set URL to: `https://abc123.ngrok.io/api/v1/webhooks/stripe`
   - Select events: `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_succeeded`, `invoice.payment_failed`
   - Copy the **Signing secret** (starts with `whsec_`)
5. **Update `backend/.env`:**
   ```env
   STRIPE_WEBHOOK_SECRET="whsec_YOUR_SECRET_FROM_STRIPE"
   ```

**Important Notes:**
- Keep the `stripe listen` command running in a separate terminal while developing
- The webhook secret from Stripe CLI is different from production webhook secrets
- Without webhooks, payments won't grant credits or create subscriptions automatically
- You can test webhooks with: `stripe trigger checkout.session.completed`

### Step 9: Access the Application

Once both servers are running:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

---

## Verification

### Check Backend Health

```bash
curl http://localhost:8000/health
```

Should return: `{"status":"ok","version":"0.1.0"}`

### Check API Documentation

Open http://localhost:8000/docs in your browser to see the interactive API documentation.

---

## Common Issues & Solutions

### Redis connection issues

**Problem**: Redis connection failed
- Ensure Redis is running: `redis-cli ping`
- Check `REDIS_URL` in `.env` matches your Redis setup
- If Redis is not available, the app will continue with in-memory rate limiting (fallback)

### Backend won't start

**Problem**: Module not found errors
```bash
# Solution: Make sure virtual environment is activated and dependencies installed
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

**Problem**: Database connection error
- Check your `DATABASE_URL` in `.env`
- Ensure the connection string uses `postgresql+asyncpg://` (not `postgresql://`)
- Verify database credentials are correct

**Problem**: Missing environment variables
- Ensure all required variables from `env.example` are set in `.env`
- Check for typos in variable names

### Frontend can't connect to backend

**Problem**: API calls failing
- Verify `NEXT_PUBLIC_API_V1_URL` in `ui/.env.local` matches backend URL
- Ensure backend is running on port 8000
- Check browser console for CORS errors

### Database migration errors

```bash
# Check current migration status
alembic current

# If needed, reset (WARNING: This will drop all tables)
alembic downgrade base
alembic upgrade head
```

---

## Production Mode

### Backend (Production)

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend (Production)

```bash
cd ui
npm run build
npm start
```

---

## Next Steps

1. **Activate Stripe Local Webhook** - See Step 8 above (required for payments to work)
2. **Seed Subscription Plans** - Run `python scripts/seed_plans.py`
3. **Test Authentication** - Create an account and test login flow
4. **Test Payments** - Try subscribing to a plan to verify webhooks are working
5. **Configure OAuth Providers** - See `backend/SUPABASE_OAUTH_SETUP.md` (optional)

---

## Getting Help

For more detailed information:

- **Full Documentation**: See `README.md`
- **Backend Setup**: See `backend/README.md` and `backend/SETUP.md`
- **Stripe Configuration**: See `backend/STRIPE_SETUP.md`
- **OAuth Setup**: See `backend/SUPABASE_OAUTH_SETUP.md`

---

## Quick Reference

| Component | Port | URL |
|-----------|------|-----|
| Frontend | 3000 | http://localhost:3000 |
| Backend API | 8000 | http://localhost:8000 |
| API Docs | 8000 | http://localhost:8000/docs |

**Backend Commands:**
```bash
# Activate venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend Commands:**
```bash
# Install dependencies
npm install

# Development
npm run dev

# Production build
npm run build
npm start
```

**Stripe Webhook Commands:**
```bash
# Login to Stripe (first time only)
stripe login

# Forward webhooks to local backend (keep this running)
stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe

# Test webhook events
stripe trigger checkout.session.completed
stripe trigger customer.subscription.created
```


