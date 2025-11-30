@echo off
echo Starting Stripe Webhook Listener...
echo Forwarding to: http://localhost:8000/api/v1/webhooks/stripe
echo.
echo ---------------------------------------------------
echo IMPORTANT:
echo 1. Look for the "Ready! Your webhook signing secret is whsec_..." line below.
echo 2. Copy that secret (starting with whsec_).
echo 3. Update your backend/.env file: STRIPE_WEBHOOK_SECRET=whsec_...
echo 4. Restart your backend server if it was already running.
echo ---------------------------------------------------
echo.
stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe
pause
