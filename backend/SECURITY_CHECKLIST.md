# Security Checklist

## Pre-Deployment Security Checklist

### Environment Configuration
- [ ] All secret keys are generated using `scripts/generate_secrets.py`
- [ ] `SECRET_KEY` is set (32+ byte hex string)
- [ ] `API_KEY_ENCRYPTION_KEY` is set (base64 encoded 32 bytes)
- [ ] `SESSION_SECRET` is set (32+ byte hex string)
- [ ] `SUPABASE_JWT_SECRET` matches Supabase project settings
- [ ] `STRIPE_WEBHOOK_SECRET` matches Stripe webhook endpoint
- [ ] Database connection string uses SSL in production
- [ ] `.env` file is NOT committed to git (check `.gitignore`)

### Access Control
- [ ] Admin emails are configured in `ADMIN_EMAILS`
- [ ] `SUPER_ADMIN_EMAIL` is set to primary admin
- [ ] Test admin access works correctly
- [ ] Regular users cannot access admin endpoints

### Network Security
- [ ] CORS origins are restricted to known domains
- [ ] `ALLOWED_HOSTS` is configured for production domain
- [ ] HTTPS is enforced in production
- [ ] Security headers are enabled (`SECURITY_HEADERS_ENABLED=true`)

### Rate Limiting
- [ ] Rate limiting is enabled (`RATE_LIMIT_ENABLED=true`)
- [ ] Rate limits are set appropriately for your use case
- [ ] Test rate limiting works (should get 429 after exceeding limits)

### Logging & Monitoring
- [ ] Audit logging is enabled (`ENABLE_AUDIT_LOGGING=true`)
- [ ] Log level is appropriate (`LOG_LEVEL=INFO` or `WARNING` in production)
- [ ] Sentry DSN is configured if using error tracking
- [ ] Logs don't contain sensitive information

### API Security
- [ ] All endpoints requiring auth use `get_current_user` dependency
- [ ] Webhook endpoints verify signatures (Stripe)
- [ ] API keys are hashed before storage
- [ ] Error messages don't expose sensitive info in production

### Database Security
- [ ] Database user has minimal required permissions
- [ ] Connection pooling is configured
- [ ] Database backups are encrypted
- [ ] SQL injection prevention (using ORM, not raw SQL)

### Dependencies
- [ ] All dependencies are up to date
- [ ] Run `pip-audit` or similar to check for vulnerabilities
- [ ] Review `requirements.txt` for known security issues

### Testing
- [ ] Test authentication flow
- [ ] Test authorization (admin vs regular user)
- [ ] Test rate limiting
- [ ] Test webhook signature verification
- [ ] Test error handling (shouldn't expose stack traces in production)

## Production Deployment

### Before Going Live
1. Generate all secrets using `scripts/generate_secrets.py`
2. Set `ENVIRONMENT=production` in `.env`
3. Disable OpenAPI docs in production (already configured)
4. Set up monitoring and alerting
5. Configure backup strategy
6. Set up SSL/TLS certificates
7. Configure firewall rules
8. Set up log aggregation

### Post-Deployment
1. Monitor logs for suspicious activity
2. Set up alerts for failed authentication attempts
3. Monitor rate limit violations
4. Review audit logs regularly
5. Keep dependencies updated
6. Rotate secrets periodically (every 90 days recommended)

