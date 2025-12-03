import stripe
import logging
import time
import asyncio
from fastapi import APIRouter, Request, Depends, Header, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.services.billing_service import BillingService
from app.db.session import get_session, async_session_maker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import UserProfile

router = APIRouter()
logger = logging.getLogger(__name__)

# Set Stripe API key
stripe.api_key = settings.STRIPE_API_KEY


async def process_webhook_event(event: dict):
    """Process webhook event in background - handles all DB operations."""
    try:
        async with async_session_maker() as session:
            service = BillingService(session)
            await service.handle_webhook(event)
            logger.info(f"✅ Successfully processed webhook: {event['type']} (id: {event.get('id')})")
    except Exception as e:
        logger.error(f"❌ Error processing webhook {event['type']}: {e}", exc_info=True)


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Stripe webhook endpoint.
    
    SECURITY: This endpoint verifies the webhook signature before processing.
    If signature verification fails, NO plans or credits will be granted.
    
    Per Stripe docs: Returns 200 immediately, processes in background.
    https://docs.stripe.com/webhooks#receive-events
    """
    payload = await request.body()
    
    # Get the Stripe signature from headers
    stripe_signature = request.headers.get("stripe-signature")
    
    if not stripe_signature:
        logger.error("❌ SECURITY: Missing stripe-signature header - rejecting webhook")
        return JSONResponse(status_code=400, content={"error": "Missing stripe-signature header"})
    
    if not settings.STRIPE_WEBHOOK_SECRET or settings.STRIPE_WEBHOOK_SECRET.strip() == "":
        logger.error("❌ SECURITY: STRIPE_WEBHOOK_SECRET is not configured - rejecting webhook")
        return JSONResponse(status_code=500, content={"error": "Webhook secret not configured"})
    
    # CRITICAL: Verify signature BEFORE processing anything
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
        logger.info(f"✅ Webhook signature verified: {event['type']} (id: {event.get('id')})")
    except ValueError as e:
        logger.error(f"❌ Invalid webhook payload: {e}")
        return JSONResponse(status_code=400, content={"error": f"Invalid payload: {str(e)}"})
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"❌ SECURITY: Invalid webhook signature - REJECTING: {e}")
        return JSONResponse(status_code=400, content={"error": f"Invalid signature: {str(e)}"})

    # Per Stripe docs: Return 200 IMMEDIATELY, process in background
    # This prevents timeouts and ensures Stripe knows we received the event
    logger.info(f"📥 Received webhook: {event['type']} - processing in background...")
    
    # Add to background tasks for async processing
    background_tasks.add_task(process_webhook_event, event)
    
    # Return 200 immediately - Stripe will not retry
    return JSONResponse(status_code=200, content={"status": "received", "event_type": event['type']})


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
                        from app.services.tiktok_conversions import TikTokConversionsService
                        from app.services.snap_conversions import SnapConversionsService
                        from app.services.ga4_service import GA4Service
                        
                        conversions_service = FacebookConversionsService()
                        tiktok_service = TikTokConversionsService()
                        snap_service = SnapConversionsService()
                        ga4_service = GA4Service()
                        
                        # Extract first and last name from display_name
                        first_name = None
                        last_name = None
                        if user_profile.display_name:
                            name_parts = user_profile.display_name.split(maxsplit=1)
                            first_name = name_parts[0] if name_parts else None
                            last_name = name_parts[1] if len(name_parts) > 1 else None
                        
                        # Generate unique event_id for deduplication
                        event_id = f"registration_{user_profile.id}_{int(time.time())}"
                        
                        logger.info(f"🎯 Triggering CompleteRegistration for verified user: {user_profile.email} (event_id: {event_id})")
                        logger.info(f"   Using stored context: IP={user_profile.signup_ip}, UA={user_profile.signup_user_agent[:50] if user_profile.signup_user_agent else None}")
                        
                        # Fire CompleteRegistration event using stored tracking context (fire and forget)
                        # Facebook tracking
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
                        
                        # TikTok tracking
                        asyncio.create_task(tiktok_service.track_complete_registration(
                            email=user_profile.email,
                            external_id=str(user_profile.id),
                            client_ip=user_profile.signup_ip,
                            client_user_agent=user_profile.signup_user_agent,
                            event_source_url=f"{settings.FRONTEND_URL}/",
                            event_id=event_id,
                            ttp=user_profile.signup_ttp,
                            ttclid=user_profile.signup_ttclid,
                        ))

                        # Snap tracking
                        asyncio.create_task(snap_service.track_complete_registration(
                            email=user_profile.email,
                            client_ip=user_profile.signup_ip,
                            client_user_agent=user_profile.signup_user_agent,
                            page_url=f"{settings.FRONTEND_URL}/",
                            sc_cookie1=user_profile.signup_sc_cookie1,
                            sc_clid=user_profile.signup_sc_clid,
                            event_id=event_id,
                            external_id=str(user_profile.id),
                        ))
                        
                        # GA4 tracking
                        if user_profile.signup_ga_client_id:
                            asyncio.create_task(ga4_service.track_sign_up(
                                client_id=user_profile.signup_ga_client_id,
                                user_id=str(user_profile.id),
                                session_id=user_profile.signup_ga_session_id,
                                client_ip=user_profile.signup_ip,
                                user_agent=user_profile.signup_user_agent,
                                page_location=f"{settings.FRONTEND_URL}/",
                                method="email"
                            ))
                        
                        logger.info(f"✅ CompleteRegistration event triggered for {user_profile.email} (FB, TikTok, Snap, GA4)")
                    except Exception as e:
                        logger.error(f"Failed to track CompleteRegistration for verified user {user_id}: {str(e)}")
                else:
                    logger.warning(f"User profile not found for verified user {user_id}")
        
        return {"status": "success", "event": event_type}
        
    except Exception as e:
        logger.error(f"Error processing Supabase auth webhook: {str(e)}", exc_info=True)
        # Return 200 anyway so Supabase doesn't retry
        return {"status": "error", "message": str(e)}
