import stripe
import logging
from fastapi import APIRouter, Request, Depends, Header, HTTPException
from app.core.config import settings
from app.services.billing_service import BillingService
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """
    Stripe webhook endpoint.
    
    SECURITY: This endpoint verifies the webhook signature before processing.
    If signature verification fails, NO plans or credits will be granted.
    """
    payload = await request.body()
    
    # Get the Stripe signature from headers (Stripe sends it as 'stripe-signature')
    stripe_signature = request.headers.get("stripe-signature")
    
    if not stripe_signature:
        logger.error("SECURITY: Missing stripe-signature header - rejecting webhook")
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")
    
    if not settings.STRIPE_WEBHOOK_SECRET or settings.STRIPE_WEBHOOK_SECRET.strip() == "":
        logger.error("SECURITY: STRIPE_WEBHOOK_SECRET is not configured or is empty - rejecting webhook")
        logger.error("SECURITY: NO credits or subscriptions will be granted without a valid webhook secret")
        raise HTTPException(
            status_code=500,
            detail="Webhook secret not configured - credits and subscriptions cannot be granted"
        )
    
    # CRITICAL: Verify signature BEFORE processing anything
    # If verification fails, we return immediately without processing
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
        logger.info(f"Webhook signature verified: {event['type']} (id: {event.get('id')})")
    except ValueError as e:
        logger.error(f"SECURITY: Invalid webhook payload - rejecting: {e}")
        # Return 400 without processing - no plans/credits granted
        raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"SECURITY: Invalid webhook signature - REJECTING WEBHOOK: {e}")
        logger.error(f"SECURITY: This webhook will NOT grant any plans or credits")
        # Return 400 without processing - no plans/credits granted
        raise HTTPException(status_code=400, detail=f"Invalid signature: {str(e)}")

    # Only process if signature is verified
    try:
        service = BillingService(session)
        await service.handle_webhook(event)
        logger.info(f"Successfully processed verified webhook: {event['type']}")
    except Exception as e:
        logger.error(f"Error processing webhook {event['type']}: {e}", exc_info=True)
        # Rollback any partial changes
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {str(e)}")
    
    return {"status": "success"}

