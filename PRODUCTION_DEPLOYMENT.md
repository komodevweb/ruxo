# Production Deployment Guide for Ruxo

This guide covers deploying Ruxo to production with:
- **Frontend**: `ruxo.ai`
- **Backend API**: `api.ruxo.ai`

## Prerequisites

### Server Requirements
- Ubuntu 22.04 LTS or similar Linux distribution
- Python 3.11+
- Node.js 20.x+
- PostgreSQL 14+
- Redis 7.x+
- Nginx
- SSL certificates (Let's Encrypt recommended)

### Domain Setup
1. Point `ruxo.ai` to your frontend server IP
2. Point `api.ruxo.ai` to your backend server IP
3. Ensure both domains have DNS A records configured

## Backend Deployment (api.ruxo.ai)

### Step 1: Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3.11 python3.11-venv python3-pip postgresql postgresql-contrib redis-server nginx git

# Install Node.js 20.x
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### Step 2: Clone Repository

```bash
# Create application directory
sudo mkdir -p /opt/ruxo
cd /opt/ruxo

# Clone your repository (replace with your repo URL)
sudo git clone <your-repo-url> .

# Or if you're uploading files:
sudo mkdir -p /opt/ruxo/backend
# Upload your backend files to /opt/ruxo/backend
```

### Step 3: Configure Environment

```bash
cd /opt/ruxo/backend

# Copy production environment template
sudo cp env.production.example .env

# Edit with your production values
sudo nano .env
```

**Important environment variables to set:**
```env
ENVIRONMENT="production"
DATABASE_URL="postgresql+asyncpg://postgres:PASSWORD@localhost:5432/ruxo"
FRONTEND_URL="https://ruxo.ai"
BACKEND_BASE_URL="https://api.ruxo.ai"
BACKEND_CORS_ORIGINS="https://ruxo.ai,https://www.ruxo.ai"
ALLOWED_HOSTS="api.ruxo.ai,ruxo.ai"
STRIPE_API_KEY="sk_live_..."  # Use LIVE keys!
```

### Step 4: Setup Database

```bash
# Create database
sudo -u postgres psql
CREATE DATABASE ruxo;
CREATE USER ruxo_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE ruxo TO ruxo_user;
\q

# Update DATABASE_URL in .env with the new user
```

### Step 5: Run Deployment Script

```bash
cd /opt/ruxo/backend
sudo chmod +x deploy.sh
sudo ./deploy.sh
```

The script will:
- Create service user
- Setup Python virtual environment
- Install dependencies
- Run database migrations
- Create systemd service
- Start the backend service

### Step 6: Configure Nginx

```bash
# Copy nginx configuration
sudo cp /opt/ruxo/backend/nginx.conf.example /etc/nginx/sites-available/ruxo-api

# Edit if needed
sudo nano /etc/nginx/sites-available/ruxo-api

# Enable site
sudo ln -s /etc/nginx/sites-available/ruxo-api /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### Step 7: Setup SSL with Let's Encrypt

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d api.ruxo.ai

# Auto-renewal is set up automatically
```

### Step 8: Verify Backend

```bash
# Check service status
sudo systemctl status ruxo-backend

# Check logs
sudo journalctl -u ruxo-backend -f

# Test API
curl https://api.ruxo.ai/health
```

## Frontend Deployment (ruxo.ai)

### Step 1: Build Frontend

```bash
cd /opt/ruxo/ui

# Install dependencies
npm install

# Create production environment file
cat > .env.production << EOF
NEXT_PUBLIC_API_URL=https://api.ruxo.ai
NEXT_PUBLIC_API_V1_URL=https://api.ruxo.ai/api/v1
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
EOF

# Build for production
npm run build
```

### Step 2: Setup PM2 or Systemd

**Option A: Using PM2 (Recommended)**

```bash
# Install PM2
sudo npm install -g pm2

# Start application
cd /opt/ruxo/ui
pm2 start npm --name "ruxo-frontend" -- start
pm2 save
pm2 startup  # Follow instructions to enable on boot
```

**Option B: Using Systemd**

```bash
sudo nano /etc/systemd/system/ruxo-frontend.service
```

```ini
[Unit]
Description=Ruxo Frontend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ruxo/ui
Environment="NODE_ENV=production"
ExecStart=/usr/bin/npm start
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable ruxo-frontend
sudo systemctl start ruxo-frontend
```

### Step 3: Configure Nginx for Frontend

```bash
sudo nano /etc/nginx/sites-available/ruxo-frontend
```

```nginx
server {
    listen 80;
    server_name ruxo.ai www.ruxo.ai;
    
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ruxo.ai www.ruxo.ai;

    ssl_certificate /etc/letsencrypt/live/ruxo.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ruxo.ai/privkey.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/ruxo-frontend /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d ruxo.ai -d www.ruxo.ai
```

## Post-Deployment Checklist

### Backend (api.ruxo.ai)
- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] Redis running and connected
- [ ] Systemd service running
- [ ] Nginx configured and SSL working
- [ ] Health check endpoint responding
- [ ] CORS configured for frontend domain
- [ ] Stripe webhook URL updated: `https://api.ruxo.ai/api/v1/billing/webhook`

### Frontend (ruxo.ai)
- [ ] Production build successful
- [ ] Environment variables set
- [ ] PM2/Systemd service running
- [ ] Nginx configured and SSL working
- [ ] API URL points to `https://api.ruxo.ai`

### Security
- [ ] SSL certificates installed and auto-renewing
- [ ] Firewall configured (allow 80, 443, 22)
- [ ] Database credentials secure
- [ ] API keys stored securely
- [ ] Rate limiting enabled
- [ ] Security headers enabled

### Monitoring
- [ ] Logs accessible and monitored
- [ ] Error tracking configured (Sentry)
- [ ] Uptime monitoring setup
- [ ] Backup strategy in place

## Useful Commands

### Backend
```bash
# View logs
sudo journalctl -u ruxo-backend -f

# Restart service
sudo systemctl restart ruxo-backend

# Check status
sudo systemctl status ruxo-backend

# Run migrations
cd /opt/ruxo/backend
source venv/bin/activate
alembic upgrade head
```

### Frontend (PM2)
```bash
# View logs
pm2 logs ruxo-frontend

# Restart
pm2 restart ruxo-frontend

# Status
pm2 status
```

### Nginx
```bash
# Test configuration
sudo nginx -t

# Reload
sudo systemctl reload nginx

# Restart
sudo systemctl restart nginx
```

## Troubleshooting

### Backend not starting
1. Check logs: `sudo journalctl -u ruxo-backend -n 50`
2. Verify .env file exists and is correct
3. Check database connection
4. Verify Redis is running: `redis-cli ping`

### CORS errors
1. Verify `BACKEND_CORS_ORIGINS` includes `https://ruxo.ai`
2. Check Nginx headers
3. Verify frontend API URL is correct

### SSL issues
1. Check certificate: `sudo certbot certificates`
2. Renew if needed: `sudo certbot renew`
3. Verify Nginx SSL configuration

### Database connection errors
1. Check PostgreSQL is running: `sudo systemctl status postgresql`
2. Verify DATABASE_URL in .env
3. Check firewall rules

## Support

For issues, check:
- Backend logs: `sudo journalctl -u ruxo-backend -f`
- Frontend logs: `pm2 logs` or `sudo journalctl -u ruxo-frontend -f`
- Nginx logs: `/var/log/nginx/error.log`

