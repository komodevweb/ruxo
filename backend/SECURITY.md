# Security Documentation for Ruxo Backend

## Overview

This document outlines the security measures implemented in the Ruxo backend API.

## Security Features

### 1. Authentication & Authorization

- **Supabase JWT Authentication**: All protected endpoints require a valid Supabase JWT token
- **Token Validation**: JWT tokens are verified using the `SUPABASE_JWT_SECRET`
- **User Auto-Provisioning**: User profiles are automatically created on first authenticated request
- **Admin Access Control**: Admin endpoints check against configured admin email list

### 2. Rate Limiting

- **Per-Minute Limit**: Configurable via `RATE_LIMIT_PER_MINUTE` (default: 60)
- **Per-Hour Limit**: Configurable via `RATE_LIMIT_PER_HOUR` (default: 1000)
- **IP-Based**: Rate limiting is applied per client IP address
- **Health Check Exemption**: `/health` endpoint is exempt from rate limiting

### 3. Security Headers

The following security headers are automatically added to all responses:

- `X-Content-Type-Options: nosniff` - Prevents MIME type sniffing
- `X-Frame-Options: DENY` - Prevents clickjacking
- `X-XSS-Protection: 1; mode=block` - XSS protection
- `Strict-Transport-Security` - Forces HTTPS
- `Referrer-Policy: strict-origin-when-cross-origin` - Controls referrer information
- `Permissions-Policy` - Restricts browser features

### 4. CORS Configuration

- **Origin Whitelist**: Only configured origins in `BACKEND_CORS_ORIGINS` are allowed
- **Credentials**: Controlled via `CORS_ALLOW_CREDENTIALS`
- **Max Age**: Configurable cache time via `CORS_MAX_AGE`

### 5. API Key Management

- **Secure Generation**: API keys are generated using `secrets.token_urlsafe()`
- **Hashing**: API keys are hashed using HMAC-SHA256 before storage
- **Verification**: Constant-time comparison to prevent timing attacks

### 6. Webhook Security

- **Stripe Webhooks**: Signature verification using `STRIPE_WEBHOOK_SECRET`
- **Timestamp Tolerance**: Configurable via `WEBHOOK_TIMESTAMP_TOLERANCE` (default: 5 minutes)
- **Event Logging**: All webhook events are logged to `webhook_event_logs` table

### 7. Database Security

- **Connection String**: Stored securely in environment variables
- **Async Connection Pooling**: Using asyncpg for efficient connection management
- **SQL Injection Prevention**: Using SQLAlchemy ORM with parameterized queries

### 8. Audit Logging

- **User Actions**: All sensitive actions are logged to `audit_logs` table
- **IP Tracking**: Client IP addresses are recorded
- **Metadata**: JSON metadata field for additional context

## Environment Variables

### Required Security Variables

```bash
# Secret Keys (Generate with: openssl rand -hex 32)
SECRET_KEY="..."                    # For API key hashing, session tokens
API_KEY_ENCRYPTION_KEY="..."       # For encrypting sensitive data (base64 encoded 32 bytes)
SESSION_SECRET="..."                # For session management

# Supabase
SUPABASE_JWT_SECRET="..."          # JWT secret from Supabase dashboard

# Stripe
STRIPE_WEBHOOK_SECRET="whsec_..."  # Webhook signing secret from Stripe

# Admin
ADMIN_EMAILS="admin@ruxo.ai"       # Comma-separated admin emails
SUPER_ADMIN_EMAIL="admin@ruxo.ai"  # Primary admin email
```

### Optional Security Variables

```bash
# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Security Headers
SECURITY_HEADERS_ENABLED=true
ALLOWED_HOSTS="localhost,127.0.0.1"

# Logging
LOG_LEVEL="INFO"
ENABLE_AUDIT_LOGGING=true
SENTRY_DSN=""                      # Optional: Error tracking

# Webhook Security
WEBHOOK_TIMESTAMP_TOLERANCE=300     # 5 minutes in seconds
```

## Generating Secure Keys

### Generate SECRET_KEY

```bash
# Linux/Mac
openssl rand -hex 32

# Windows PowerShell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
```

### Generate API_KEY_ENCRYPTION_KEY

```bash
# Linux/Mac
openssl rand -base64 32

# Windows PowerShell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
```

## Security Best Practices

### 1. Environment Variables

- **Never commit `.env` files** to version control
- Use `.env.example` as a template
- Rotate secrets regularly
- Use different secrets for development, staging, and production

### 2. Database

- Use connection pooling
- Limit database user permissions
- Enable SSL/TLS for database connections
- Regularly backup and encrypt backups

### 3. API Keys

- Store hashed versions only
- Never log or expose API keys
- Implement key rotation policies
- Revoke compromised keys immediately

### 4. Rate Limiting

- Monitor rate limit violations
- Adjust limits based on legitimate usage patterns
- Consider implementing per-user rate limits for authenticated users

### 5. Logging

- Log security events (failed auth, rate limit violations, etc.)
- Don't log sensitive data (passwords, tokens, API keys)
- Use structured logging
- Monitor logs for suspicious activity

### 6. HTTPS

- Always use HTTPS in production
- Enforce HTTPS via `Strict-Transport-Security` header
- Use valid SSL certificates
- Consider certificate pinning for mobile apps

### 7. Dependencies

- Regularly update dependencies
- Use `pip-audit` or similar tools to check for vulnerabilities
- Pin dependency versions in `requirements.txt`
- Review security advisories

## Security Checklist

- [ ] All secret keys are generated and set in `.env`
- [ ] `SECRET_KEY` is unique and random (32+ bytes)
- [ ] `API_KEY_ENCRYPTION_KEY` is base64 encoded 32 bytes
- [ ] `SUPABASE_JWT_SECRET` matches Supabase dashboard
- [ ] `STRIPE_WEBHOOK_SECRET` matches Stripe dashboard
- [ ] Admin emails are configured correctly
- [ ] CORS origins are restricted to known domains
- [ ] Rate limiting is enabled and configured appropriately
- [ ] Security headers are enabled
- [ ] Database connection uses SSL in production
- [ ] `.env` file is in `.gitignore`
- [ ] Logging is configured appropriately
- [ ] Error messages don't expose sensitive information in production

## Incident Response

If a security incident occurs:

1. **Immediately rotate all secrets** (SECRET_KEY, API keys, etc.)
2. **Review audit logs** for suspicious activity
3. **Revoke compromised API keys** from the database
4. **Notify affected users** if personal data was compromised
5. **Document the incident** and remediation steps

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/advanced/security/)
- [Supabase Security](https://supabase.com/docs/guides/auth/security)
- [Stripe Webhook Security](https://stripe.com/docs/webhooks/signatures)

