# Production Quick Start Checklist

## Before You Start

1. **Domain DNS Setup**
   - Point `ruxo.ai` → Frontend server IP
   - Point `api.ruxo.ai` → Backend server IP
   - Wait for DNS propagation (can take up to 48 hours)

2. **Server Requirements**
   - Ubuntu 22.04+ or similar
   - Minimum 2GB RAM, 2 CPU cores
   - Python 3.11+, Node.js 20+, PostgreSQL 14+, Redis 7+

## Backend Deployment (5 Minutes)

```bash
# 1. Clone/upload code to server
sudo mkdir -p /opt/ruxo/backend
cd /opt/ruxo/backend
# Upload your backend files here

# 2. Run deployment script
sudo chmod +x deploy.sh
sudo ./deploy.sh

# 3. Edit environment file
sudo nano .env
# Set: FRONTEND_URL, BACKEND_BASE_URL, DATABASE_URL, etc.

# 4. Setup SSL
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.ruxo.ai

# 5. Restart service
sudo systemctl restart ruxo-backend
```

## Frontend Deployment (5 Minutes)

```bash
# 1. Upload frontend code
cd /opt/ruxo/ui

# 2. Install and build
npm install
cp env.production.template .env.production
nano .env.production  # Set API URLs
npm run build

# 3. Start with PM2
sudo npm install -g pm2
pm2 start npm --name "ruxo-frontend" -- start
pm2 save
pm2 startup

# 4. Setup SSL
sudo certbot --nginx -d ruxo.ai -d www.ruxo.ai
```

## Critical Environment Variables

### Backend (.env)
```env
ENVIRONMENT="production"
FRONTEND_URL="https://ruxo.ai"
BACKEND_BASE_URL="https://api.ruxo.ai"
BACKEND_CORS_ORIGINS="https://ruxo.ai,https://www.ruxo.ai"
STRIPE_API_KEY="sk_live_..."  # LIVE key!
```

### Frontend (.env.production)
```env
NEXT_PUBLIC_API_URL="https://api.ruxo.ai"
NEXT_PUBLIC_API_V1_URL="https://api.ruxo.ai/api/v1"
```

## Verify Deployment

```bash
# Backend health check
curl https://api.ruxo.ai/health

# Frontend
curl https://ruxo.ai

# Check services
sudo systemctl status ruxo-backend
pm2 status
```

## Common Issues

**CORS Errors?**
- Check `BACKEND_CORS_ORIGINS` includes `https://ruxo.ai`
- Verify frontend API URL is correct

**Service won't start?**
- Check logs: `sudo journalctl -u ruxo-backend -f`
- Verify .env file exists and has correct values

**SSL Issues?**
- Run: `sudo certbot certificates`
- Renew: `sudo certbot renew`

## Next Steps

1. Update Stripe webhook URL: `https://api.ruxo.ai/api/v1/billing/webhook`
2. Test authentication flow
3. Test payment flow
4. Setup monitoring (Sentry, uptime monitoring)
5. Configure backups

For detailed instructions, see `PRODUCTION_DEPLOYMENT.md`

