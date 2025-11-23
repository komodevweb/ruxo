# Cloudflare SSL Setup Guide

This guide shows you how to set up Cloudflare Origin Certificates for `api.ruxo.ai`.

## Prerequisites

1. Domain `api.ruxo.ai` added to Cloudflare
2. DNS record pointing to your server IP
3. Cloudflare account with access to the domain

## Step 1: Get Cloudflare Origin Certificate

1. **Login to Cloudflare Dashboard**
   - Go to https://dash.cloudflare.com
   - Select your domain (`ruxo.ai`)

2. **Navigate to SSL/TLS**
   - Click on **SSL/TLS** in the left sidebar
   - Click on **Origin Server** tab
   - Click **Create Certificate**

3. **Configure Certificate**
   - **Private key type**: RSA (2048) - recommended
   - **Hostnames**: 
     - `api.ruxo.ai`
     - `*.ruxo.ai` (optional, for subdomains)
   - **Certificate Validity**: 15 years (default)
   - Click **Create**

4. **Download Certificates**
   - Copy the **Origin Certificate** (this is the `.pem` file)
   - Copy the **Private Key** (this is the `.key` file)
   - **Important**: Save these securely - you won't be able to see the private key again!

## Step 2: Install Certificates on Server

```bash
# Create SSL directory
sudo mkdir -p /etc/nginx/ssl

# Create certificate file
sudo nano /etc/nginx/ssl/cloudflare-origin.pem
# Paste the Origin Certificate content here
# Save and exit (Ctrl+X, Y, Enter)

# Create private key file
sudo nano /etc/nginx/ssl/cloudflare-origin.key
# Paste the Private Key content here
# Save and exit (Ctrl+X, Y, Enter)

# Set proper permissions
sudo chmod 600 /etc/nginx/ssl/cloudflare-origin.key
sudo chmod 644 /etc/nginx/ssl/cloudflare-origin.pem
sudo chown root:root /etc/nginx/ssl/cloudflare-origin.*
```

## Step 3: Configure Cloudflare SSL Mode

1. **In Cloudflare Dashboard**
   - Go to **SSL/TLS** > **Overview**
   - Set SSL/TLS encryption mode to **Full (strict)**
   - This ensures end-to-end encryption

2. **Why Full (Strict)?**
   - **Full**: Encrypts traffic but doesn't verify certificate
   - **Full (Strict)**: Encrypts AND verifies your origin certificate ✅ **Recommended**

## Step 4: Test and Reload Nginx

```bash
# Test Nginx configuration
sudo nginx -t

# If test passes, reload Nginx
sudo systemctl reload nginx

# Check status
sudo systemctl status nginx
```

## Step 5: Verify SSL

```bash
# Test from server
curl -I https://api.ruxo.ai/health

# Or test from browser
# Visit: https://api.ruxo.ai/health
```

## Step 6: Update Cloudflare DNS

1. **In Cloudflare Dashboard**
   - Go to **DNS** > **Records**
   - Find `api.ruxo.ai` A record
   - Click the **orange cloud** to enable proxy (recommended)
   - This enables Cloudflare's CDN and DDoS protection

## Important Notes

### Certificate Renewal
- Cloudflare Origin Certificates are valid for **15 years**
- No automatic renewal needed
- You'll need to manually renew before expiration

### Cloudflare Proxy (Orange Cloud)
- **Enabled (Orange)**: Traffic goes through Cloudflare (recommended)
  - DDoS protection
  - CDN caching
  - Better performance
  - Uncomment `real_ip_header CF-Connecting-IP` in Nginx config

- **Disabled (Gray)**: Direct connection to your server
  - No Cloudflare features
  - Direct IP access

### SSL Modes Explained

| Mode | Description | Use Case |
|------|-------------|----------|
| **Off** | No encryption | ❌ Never use |
| **Flexible** | Encrypts Cloudflare ↔ Visitor only | ⚠️ Not secure for APIs |
| **Full** | Encrypts both, but doesn't verify | ⚠️ Less secure |
| **Full (Strict)** | Encrypts both AND verifies | ✅ **Recommended** |

## Troubleshooting

### Certificate not working?
1. Check certificate files exist:
   ```bash
   ls -la /etc/nginx/ssl/
   ```

2. Check file permissions:
   ```bash
   sudo chmod 600 /etc/nginx/ssl/cloudflare-origin.key
   sudo chmod 644 /etc/nginx/ssl/cloudflare-origin.pem
   ```

3. Check Nginx error logs:
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

### SSL handshake errors?
- Verify Cloudflare SSL mode is set to **Full (Strict)**
- Check that certificate hostname matches domain
- Ensure certificate hasn't expired

### Can't access via HTTPS?
- Check firewall allows port 443:
  ```bash
  sudo ufw allow 443/tcp
  ```
- Verify DNS is pointing to correct IP
- Check Cloudflare proxy is enabled (orange cloud)

## Security Best Practices

1. ✅ Use **Full (Strict)** SSL mode
2. ✅ Keep certificate files secure (600 permissions)
3. ✅ Enable Cloudflare proxy for DDoS protection
4. ✅ Regularly check certificate expiration
5. ✅ Monitor Nginx logs for SSL errors

## Quick Reference

```bash
# View certificate expiration
openssl x509 -in /etc/nginx/ssl/cloudflare-origin.pem -noout -dates

# Test SSL connection
openssl s_client -connect api.ruxo.ai:443 -servername api.ruxo.ai

# Reload Nginx after config changes
sudo systemctl reload nginx
```

