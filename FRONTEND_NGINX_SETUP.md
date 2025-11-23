# Frontend Nginx Setup for ruxo.ai

## Current Setup
- **Backend**: `api.ruxo.ai` ✅ (SSL configured)
- **Frontend**: `ruxo.ai` (needs SSL certificate)

## Step 1: Get Cloudflare Certificate for ruxo.ai

1. Go to Cloudflare Dashboard → SSL/TLS → Origin Server
2. Create a new certificate for:
   - `ruxo.ai`
   - `www.ruxo.ai`
   - `*.ruxo.ai` (optional, for subdomains)
3. Download the certificate and private key

## Step 2: Install Certificate

```bash
# Save certificate
sudo nano /etc/nginx/ssl/cloudflare-origin-ruxo.pem
# Paste the certificate content

# Save private key
sudo nano /etc/nginx/ssl/cloudflare-origin-ruxo.key
# Paste the private key content

# Set permissions
sudo chmod 600 /etc/nginx/ssl/cloudflare-origin-ruxo.key
sudo chmod 644 /etc/nginx/ssl/cloudflare-origin-ruxo.pem
sudo chown root:root /etc/nginx/ssl/cloudflare-origin-ruxo.*
```

## Step 3: Enable Frontend Nginx Config

The configuration is already created at `/etc/nginx/sites-available/ruxo-frontend`.

After installing the certificate, test and reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Step 4: Start Frontend

Make sure your Next.js frontend is running on port 3000:

```bash
cd /opt/ruxo/ui  # or wherever your frontend is
npm run build
pm2 start npm --name "ruxo-frontend" -- start
# OR
npm start
```

## Step 5: Verify

```bash
# Test HTTPS
curl -k https://ruxo.ai

# Check Nginx status
sudo systemctl status nginx
```

## Important Notes

1. **Frontend Environment Variables**: Make sure `.env.production` has:
   ```env
   NEXT_PUBLIC_API_URL=https://api.ruxo.ai
   NEXT_PUBLIC_API_V1_URL=https://api.ruxo.ai/api/v1
   ```

2. **Cloudflare SSL Mode**: Set to **Full (Strict)** for both domains

3. **DNS**: Ensure both `ruxo.ai` and `www.ruxo.ai` point to your server

4. **Port 3000**: Make sure nothing else is using port 3000

