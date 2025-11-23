import stripe
import logging
import time
from fastapi import APIRouter, Request, Depends, Header, HTTPException
from app.core.config import settings
from app.services.billing_service import BillingService
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import UserProfile

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

@router.post("/supabase-auth")
async def supabase_auth_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """
    Supabase Auth webhook endpoint.
    
    Handles auth events from Supabase including:
    - user.created: When a new user signs up
    - user.updated: When a user's email is verified
    
    This is used to fire CompleteRegistration event when email is verified.
    """
    try:
        payload = await request.json()
        event_type = payload.get("type")
        event_data = payload.get("record", {})
        
        logger.info(f"📬 Supabase Auth Webhook: {event_type}")
        logger.debug(f"Webhook payload: {payload}")
        
        # Handle user email verification
        if event_type == "user.updated":
            user_id = event_data.get("id")
            email = event_data.get("email")
            email_confirmed_at = event_data.get("email_confirmed_at")
            
            # Check if email was just verified (email_confirmed_at changed from None to a timestamp)
            if user_id and email and email_confirmed_at:
                logger.info(f"✉️ Email verified for user: {email} ({user_id})")
                
                # Get user profile from our database
                result = await session.execute(
                    select(UserProfile).where(UserProfile.id == user_id)
                )
                user_profile = result.scalar_one_or_none()
                
                if user_profile:
                    # Track CompleteRegistration now that email is verified
                    # Use stored tracking context from signup
                    try:
                        from app.services.facebook_conversions import FacebookConversionsService
                        
                        conversions_service = FacebookConversionsService()
                        
                        # Extract first and last name from display_name
                        first_name = None
                        last_name = None
                        if user_profile.display_name:
                            name_parts = user_profile.display_name.split(maxsplit=1)
                            first_name = name_parts[0] if name_parts else None
                            last_name = name_parts[1] if len(name_parts) > 1 else None
                        
                        # Generate unique event_id for deduplication
                        import asyncio
                        event_id = f"registration_{user_profile.id}_{int(time.time())}"
                        
                        logger.info(f"🎯 Triggering CompleteRegistration for verified user: {user_profile.email} (event_id: {event_id})")
                        logger.info(f"   Using stored context: IP={user_profile.signup_ip}, UA={user_profile.signup_user_agent[:50] if user_profile.signup_user_agent else None}")
                        
                        # Fire CompleteRegistration event using stored tracking context (fire and forget)
                        asyncio.create_task(conversions_service.track_complete_registration(
                            email=user_profile.email,
                            first_name=first_name,
                            last_name=last_name,
                            external_id=str(user_profile.id),
                            client_ip=user_profile.signup_ip,
                            client_user_agent=user_profile.signup_user_agent,
                            fbp=user_profile.signup_fbp,
                            fbc=user_profile.signup_fbc,
                            event_source_url=f"{settings.FRONTEND_URL}/",
                            event_id=event_id,
                        ))
                        
                        logger.info(f"✅ CompleteRegistration event triggered for {user_profile.email}")
                    except Exception as e:
                        logger.error(f"Failed to track CompleteRegistration for verified user {user_id}: {str(e)}")
                else:
                    logger.warning(f"User profile not found for verified user {user_id}")
        
        return {"status": "success", "event": event_type}
        
    except Exception as e:
        logger.error(f"Error processing Supabase auth webhook: {str(e)}", exc_info=True)
        # Return 200 anyway so Supabase doesn't retry
        return {"status": "error", "message": str(e)}

