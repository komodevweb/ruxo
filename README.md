# Ruxo - AI Content Generation Platform

Ruxo is a comprehensive AI-powered content generation platform that enables users to create stunning images and videos using advanced AI models. The platform supports text-to-image, text-to-video, image-to-video, and image animation (Wan Animate) workflows.

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [Environment Variables](#environment-variables)
- [Database Setup](#database-setup)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Services Integration](#services-integration)
- [Scripts and Utilities](#scripts-and-utilities)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## Features

### 🎨 Image Generation
- **Text-to-Image**: Generate images from text prompts using various AI models
- **Image Editing**: Edit and transform existing images
- Multiple resolutions and output formats (JPEG, PNG)
- Support for various aspect ratios

### 🎬 Video Generation
- **Text-to-Video**: Create videos from text descriptions
- **Image-to-Video**: Transform static images into dynamic videos
- **Wan Animate**: Animate images using video templates
- Multiple resolutions (480p, 720p, 1080p)
- Configurable duration and audio options

### 💳 Subscription Management
- Multiple subscription tiers (Starter, Pro, Creator, Ultimate)
- Monthly and yearly billing options
- 40% discount on yearly plans
- Credit-based system for generations
- Stripe integration for payments

### 🔐 Authentication
- Email/password authentication via Supabase
- OAuth providers (Microsoft/Azure, Google, Apple)
- JWT-based session management
- Secure cookie-based authentication

### 📦 File Storage
- Backblaze B2 cloud storage integration
- User-specific folder structure
- Automatic file organization
- Public URL generation for generated content

## Tech Stack

### Backend
- **Framework**: FastAPI 0.115.0
- **Language**: Python 3.11+
- **Database**: PostgreSQL with AsyncPG
- **ORM**: SQLAlchemy 2.0 + SQLModel
- **Authentication**: Supabase Auth, JWT
- **Payment**: Stripe
- **Storage**: Backblaze B2
- **AI Provider**: WaveSpeed AI
- **Task Scheduling**: APScheduler
- **Migrations**: Alembic

### Frontend
- **Framework**: Next.js 16.0.3
- **Language**: TypeScript 5
- **UI Library**: React 19.2.0
- **Styling**: Tailwind CSS 4
- **Components**: Headless UI
- **Image Optimization**: Next.js Image component

## Architecture

```
┌─────────────────┐         ┌─────────────────┐
│   Next.js UI    │◄───────►│   FastAPI API   │
│   (Port 3000)   │  HTTP   │   (Port 8000)   │
└─────────────────┘         └─────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
              ┌─────▼─────┐    ┌──────▼──────┐   ┌──────▼──────┐
              │ PostgreSQL │    │   Supabase   │   │  Backblaze  │
              │  Database  │    │     Auth     │   │      B2     │
              └────────────┘    └──────────────┘   └─────────────┘
                                      │
                                ┌─────▼─────┐
                                │   Stripe   │
                                │  Payments  │
                                └────────────┘
                                      │
                                ┌─────▼─────┐
                                │ WaveSpeed  │
                                │     AI     │
                                └────────────┘
```

## Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js** 20.x or later
- **Python** 3.11 or later
- **PostgreSQL** 14+ (or use Supabase hosted database)
- **Git**

### Services Required

1. **Supabase Account** - For authentication and database
2. **Stripe Account** - For payment processing
3. **Backblaze B2 Account** - For file storage
4. **WaveSpeed AI Account** - For AI content generation
5. **Azure AD App** (optional) - For Microsoft OAuth

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd ruxo
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp env.example .env

# Edit .env with your configuration
# (See Environment Variables section)
```

### 3. Frontend Setup

```bash
cd ui

# Install dependencies
npm install

# Copy environment variables
cp env.example .env.local

# Edit .env.local with your configuration
```

### 4. Database Setup

```bash
cd backend

# Run migrations
alembic upgrade head

# Seed initial data (optional)
python scripts/seed_plans.py
```

### 5. Run the Application

**Terminal 1 - Backend:**
```bash
cd backend
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd ui
npm run dev
```

The application will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Detailed Setup

### Backend Setup

#### 1. Create Virtual Environment

```bash
cd backend
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

#### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 3. Configure Environment Variables

Copy `env.example` to `.env` and configure:

```bash
cp env.example .env
```

Key environment variables to configure:

- **Database**: `DATABASE_URL` (PostgreSQL connection string)
- **Supabase**: `SUPABASE_URL`, `SUPABASE_JWT_SECRET`
- **Stripe**: `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`
- **Backblaze B2**: `B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`
- **WaveSpeed AI**: `WAVESPEED_API_KEY`, `WAVESPEED_API_URL`
- **Secrets**: `SECRET_KEY`, `API_KEY_ENCRYPTION_KEY` (generate with `python scripts/generate_secrets.py`)

#### 4. Database Migration

```bash
# Run migrations
alembic upgrade head

# Create initial data (optional)
python scripts/seed_plans.py
```

#### 5. Run Backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

#### 1. Install Dependencies

```bash
cd ui
npm install
```

#### 2. Configure Environment Variables

Create `.env.local` file:

```env
NEXT_PUBLIC_API_V1_URL=http://localhost:8000/api/v1
```

#### 3. Run Frontend

```bash
npm run dev
```

The frontend will be available at http://localhost:3000

## Environment Variables

### Backend Environment Variables

See `backend/env.example` for the complete list. Key variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | ✅ Yes |
| `SUPABASE_URL` | Supabase project URL | ✅ Yes |
| `SUPABASE_JWT_SECRET` | Supabase JWT secret | ✅ Yes |
| `STRIPE_API_KEY` | Stripe secret key | ✅ Yes |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook secret | ✅ Yes |
| `B2_APPLICATION_KEY_ID` | Backblaze B2 key ID | ✅ Yes |
| `B2_APPLICATION_KEY` | Backblaze B2 application key | ✅ Yes |
| `B2_BUCKET_NAME` | Backblaze B2 bucket name | ✅ Yes |
| `WAVESPEED_API_KEY` | WaveSpeed AI API key | ✅ Yes |
| `WAVESPEED_API_URL` | WaveSpeed AI API URL | ✅ Yes |
| `SECRET_KEY` | Application secret key | ✅ Yes |
| `FRONTEND_URL` | Frontend URL | ✅ Yes |
| `BACKEND_BASE_URL` | Backend base URL | ✅ Yes |

### Frontend Environment Variables

See `ui/env.example`. Key variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_API_V1_URL` | Backend API URL | ✅ Yes |

## Database Setup

### 1. Create PostgreSQL Database

```sql
CREATE DATABASE ruxo;
```

Or use Supabase hosted database.

### 2. Run Migrations

```bash
cd backend
alembic upgrade head
```

### 3. Seed Initial Data (Optional)

```bash
python scripts/seed_plans.py
```

This creates Stripe products/prices and database plan records.

## Running the Application

### Development Mode

**Backend:**
```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd ui
npm run dev
```

### Production Mode

**Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Frontend:**
```bash
cd ui
npm run build
npm start
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/signup` - User registration
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/auth/me` - Get current user
- `GET /api/v1/auth/oauth/{provider}` - OAuth redirect (azure, google)
- `POST /api/v1/auth/oauth/exchange` - OAuth token exchange

### Image Generation
- `GET /api/v1/image/models` - List available models
- `POST /api/v1/image/submit` - Submit image generation job
- `GET /api/v1/image/status/{job_id}` - Get job status
- `GET /api/v1/image/jobs` - List user's jobs
- `GET /api/v1/image/calculate-credits` - Calculate credit cost

### Text-to-Video
- `GET /api/v1/text-to-video/models` - List available models
- `POST /api/v1/text-to-video/submit` - Submit text-to-video job
- `GET /api/v1/text-to-video/status/{job_id}` - Get job status
- `GET /api/v1/text-to-video/all-jobs` - List user's jobs
- `GET /api/v1/text-to-video/calculate-credits` - Calculate credit cost

### Image-to-Video
- `GET /api/v1/image-to-video/models` - List available models
- `POST /api/v1/image-to-video/submit` - Submit image-to-video job
- `GET /api/v1/image-to-video/status/{job_id}` - Get job status
- `GET /api/v1/image-to-video/jobs` - List user's jobs
- `GET /api/v1/image-to-video/calculate-credits` - Calculate credit cost

### Wan Animate
- `POST /api/v1/wan-animate/submit` - Submit wan animate job
- `GET /api/v1/wan-animate/status/{job_id}` - Get job status
- `GET /api/v1/wan-animate/jobs` - List user's jobs
- `GET /api/v1/wan-animate/calculate-credits` - Calculate credit cost

### Storage
- `POST /api/v1/storage/upload/wan-animate` - Upload file for wan-animate
- `POST /api/v1/storage/upload/image-to-video` - Upload file for image-to-video
- `POST /api/v1/storage/upload/text-to-video` - Upload audio file
- `POST /api/v1/storage/upload/image-to-image` - Upload image file
- `GET /api/v1/storage/files` - List user files

### Billing
- `GET /api/v1/billing/plans` - List subscription plans
- `POST /api/v1/billing/checkout` - Create Stripe checkout session
- `POST /api/v1/billing/customer-portal` - Create customer portal session
- `POST /api/v1/billing/webhook` - Stripe webhook handler

### Credits
- `GET /api/v1/credits/balance` - Get user credit balance
- `GET /api/v1/credits/history` - Get credit transaction history

## Services Integration

### Supabase Setup

1. Create a Supabase project at https://supabase.com
2. Get your project URL and JWT secret from Settings > API
3. Configure OAuth providers in Authentication > Providers
4. See `backend/SUPABASE_OAUTH_SETUP.md` for detailed OAuth setup

### Stripe Setup

1. Create a Stripe account at https://stripe.com
2. Get your API keys from Dashboard > Developers > API keys
3. Create webhook endpoint: `https://your-domain.com/api/v1/billing/webhook`
4. Get webhook secret from Dashboard > Developers > Webhooks
5. See `backend/STRIPE_SETUP.md` for detailed setup

### Backblaze B2 Setup

1. Create a Backblaze account at https://www.backblaze.com
2. Create a bucket (recommended: `ruxo-media`)
3. Create an application key with read/write permissions
4. Get your Application Key ID and Application Key
5. Configure bucket name in environment variables

### WaveSpeed AI Setup

1. Create an account at https://wavespeed.ai
2. Get your API key from the dashboard
3. Configure API URL (default: `https://api.wavespeed.ai/api/v3`)
4. See WaveSpeed documentation for supported models and parameters

## Scripts and Utilities

### Backend Scripts

Located in `backend/scripts/`:

- `generate_secrets.py` - Generate secret keys for encryption
- `seed_plans.py` - Seed Stripe products and database plans
- `reset_monthly_credits.py` - Reset monthly credits for yearly plans
- `test_credit_reset.py` - Test credit reset logic
- `configure_azure_oauth.py` - Configure Azure OAuth in Supabase

### Frontend Scripts

Located in `ui/scripts/`:

- `convert-to-webp.js` - Convert images to WebP format

## Deployment

### Backend Deployment

1. Set environment variables on your hosting platform
2. Install dependencies: `pip install -r requirements.txt`
3. Run migrations: `alembic upgrade head`
4. Start server: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### Frontend Deployment

1. Set environment variables
2. Build: `npm run build`
3. Start: `npm start`

Or deploy to Vercel/Netlify with automatic builds.

### Database Migrations

Always run migrations before deployment:

```bash
alembic upgrade head
```

### Webhook Configuration

Configure Stripe webhook endpoint:
- URL: `https://your-domain.com/api/v1/billing/webhook`
- Events: `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`

## Troubleshooting

### Common Issues

#### Backend won't start
- Check database connection: `DATABASE_URL` is correct
- Verify all required environment variables are set
- Check Python version: `python --version` (should be 3.11+)

#### Frontend can't connect to backend
- Verify `NEXT_PUBLIC_API_V1_URL` in `.env.local`
- Check CORS settings in backend
- Ensure backend is running on the correct port

#### Authentication issues
- Verify Supabase credentials are correct
- Check JWT secret matches Supabase dashboard
- Clear browser cookies and try again

#### File upload failures
- Verify Backblaze B2 credentials
- Check bucket name and permissions
- Ensure application key has read/write permissions

#### Payment processing issues
- Verify Stripe API keys are correct
- Check webhook endpoint is accessible
- Verify webhook secret matches Stripe dashboard

### Logs

Backend logs are displayed in the terminal. For production, configure logging level:

```env
LOG_LEVEL=INFO  # or DEBUG, WARNING, ERROR
```

### Getting Help

For detailed setup guides, see:
- `backend/SETUP.md` - Backend setup guide
- `backend/STRIPE_SETUP.md` - Stripe configuration
- `backend/SUPABASE_OAUTH_SETUP.md` - OAuth setup
- `backend/WEBHOOK_SETUP.md` - Webhook configuration

## License

[Your License Here]

## Contributing

[Contributing Guidelines Here]

## Support

For issues and questions, please open an issue on GitHub or contact [your support email].

