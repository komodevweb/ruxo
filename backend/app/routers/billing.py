from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, List
from app.schemas.billing import CheckoutSessionCreate, CheckoutSessionResponse, PortalSessionResponse
from app.core.security import get_current_user, get_current_user_token
from app.models.user import UserProfile
from app.models.billing import Plan
from app.services.billing_service import BillingService
from app.utils.request_helpers import get_client_ip
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
import time

logger = logging.getLogger(__name__)

router = APIRouter()
security_optional = HTTPBearer(auto_error=False)

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    session: AsyncSession = Depends(get_session)
) -> Optional[UserProfile]:
    """Get current user if authenticated, otherwise return None."""
    if not credentials:
        return None
    try:
        payload = await get_current_user_token(credentials)
        return await get_current_user(payload, session)
    except Exception:
        return None

# Plans cache now uses Redis (see get_plans function)

def invalidate_plans_cache():
    """Invalidate the plans cache in Redis (call this when plans are updated)."""
    from app.utils.cache import invalidate_cache
    import asyncio
    # Note: This is a sync function, but cache operations are async
    # In practice, call invalidate_cache directly from async contexts
    pass

@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    data: CheckoutSessionCreate,
    request: Request,
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    # Capture tracking context for later Purchase event
    client_ip = get_client_ip(request)
    client_user_agent = request.headers.get("user-agent")
    # Facebook cookies
    fbp = request.cookies.get("_fbp")
    fbc = request.cookies.get("_fbc")
    # TikTok cookies
    ttp = request.cookies.get("_ttp")
    ttclid = request.cookies.get("_ttclid") or request.cookies.get("ttclid")
    
    # Google Ads cookies/params
    gclid = request.query_params.get("gclid") or request.cookies.get("gclid") or request.cookies.get("_gcl_aw")
    gbraid = request.query_params.get("gbraid") or request.cookies.get("gbraid")
    wbraid = request.query_params.get("wbraid") or request.cookies.get("wbraid")
    
    # GA4 cookies
    ga_client_id = None
    ga_session_id = None
    ga_cookie = request.cookies.get("_ga")
    if ga_cookie:
        parts = ga_cookie.split('.')
        if len(parts) >= 2:
            ga_client_id = '.'.join(parts[-2:])
        else:
            ga_client_id = ga_cookie
    # Try to find session ID cookie
    for cookie_name, cookie_value in request.cookies.items():
        if cookie_name.startswith("_ga_"):
            parts = cookie_value.split(".")
            if len(parts) > 2:
                ga_session_id = parts[2]
                break
    
    # If fbc cookie is not set but fbclid is in URL, create fbc from fbclid
    # Per Facebook docs: fbc format is fb.1.{timestamp}.{fbclid}
    if not fbc:
        fbclid = request.query_params.get("fbclid")
        if fbclid:
            import time
            fbc = f"fb.1.{int(time.time() * 1000)}.{fbclid}"
            logger.info(f"💳 [CHECKOUT] Created fbc from fbclid URL parameter: {fbc}")
    
    logger.info(f"💳 [CHECKOUT] Creating checkout session for user {current_user.id}")
    logger.info(f"💳 [CHECKOUT] Captured tracking context: IP={client_ip}, UA={client_user_agent[:50] if client_user_agent else 'None'}..., fbp={fbp}, fbc={fbc}, ga_client_id={ga_client_id}")
    
    # Store tracking context in user profile for fallback (in case metadata is missing in webhook)
    current_user.last_checkout_ip = client_ip
    current_user.last_checkout_user_agent = client_user_agent
    current_user.last_checkout_fbp = fbp
    current_user.last_checkout_fbc = fbc
    current_user.last_checkout_ga_client_id = ga_client_id
    current_user.last_checkout_ga_session_id = ga_session_id
    current_user.last_checkout_timestamp = datetime.utcnow()
    session.add(current_user)
    await session.commit()
    logger.info(f"💳 [CHECKOUT] Stored tracking context in user profile for fallback")
    
    service = BillingService(session)
    url = await service.create_checkout_session(
        user=current_user,
        plan_name=data.plan_name,
        client_ip=client_ip,
        client_user_agent=client_user_agent,
        fbp=fbp,
        fbc=fbc,
        ttp=ttp,
        ttclid=ttclid,
        gclid=gclid,
        gbraid=gbraid,
        wbraid=wbraid,
        ga_client_id=ga_client_id,
        ga_session_id=ga_session_id,
    )
    return CheckoutSessionResponse(url=url)

@router.post("/create-portal-session", response_model=PortalSessionResponse)
async def create_portal_session(
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    service = BillingService(session)
    try:
        url = await service.create_portal_session(current_user)
        return PortalSessionResponse(url=url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/plans")
async def get_plans(
    response: Response,
    session: AsyncSession = Depends(get_session)
):
    """Get all active subscription plans (cached in Redis for 1 hour)."""
    from app.utils.cache import get_cached, set_cached, cache_key
    
    cache_key_str = cache_key("cache", "billing", "plans_v2")
    
    # Try Redis cache first
    cached = await get_cached(cache_key_str)
    if cached is not None:
        if response:
            response.headers["Cache-Control"] = "public, max-age=300"  # 5 min browser cache
            response.headers["X-Cache"] = "HIT"
        return cached
    
    # Cache miss - fetch from database
    # Exclude free_trial plan from list (it's assigned automatically during trial, not selectable)
    result = await session.execute(
        select(Plan).where(
            Plan.is_active == True,
            Plan.name != "free_trial"
        ).order_by(Plan.amount_cents)
    )
    plans = result.scalars().all()
    
    # Format response with 40% discount for yearly plans
    plans_data = []
    for plan in plans:
        amount_cents = plan.amount_cents
        amount_dollars = plan.amount_cents / 100
        
        # Apply 40% discount to yearly plans (60% of original price)
        if plan.interval == "year":
            original_amount_cents = amount_cents
            original_amount_dollars = amount_dollars
            amount_cents = int(amount_cents * 0.6)  # 40% off = 60% of original
            amount_dollars = amount_cents / 100
        else:
            original_amount_cents = None
            original_amount_dollars = None
        
        # Format interval display - handle one_time specially
        interval_display = plan.interval
        if plan.interval == "one_time":
            interval_display = "one-time"
        
        plans_data.append({
            "id": str(plan.id),
            "name": plan.name,
            "display_name": plan.display_name,
            "amount_cents": amount_cents,
            "amount_dollars": amount_dollars,
            "original_amount_cents": original_amount_cents,
            "original_amount_dollars": original_amount_dollars,
            "interval": plan.interval,
            "interval_display": interval_display,
            "credits_per_month": plan.credits_per_month,
            "currency": plan.currency,
            "trial_days": getattr(plan, "trial_days", 0),
            "trial_amount_cents": getattr(plan, "trial_amount_cents", 0),
            "trial_amount_dollars": getattr(plan, "trial_amount_cents", 0) / 100.0,
            "trial_credits": getattr(plan, "trial_credits", 0),
        })
    
    # Cache in Redis for 1 hour
    await set_cached(cache_key_str, plans_data, ttl=3600)
    
    # Set cache headers
    if response:
        response.headers["Cache-Control"] = "public, max-age=300"  # 5 min browser cache
        response.headers["X-Cache"] = "MISS"
    
    return plans_data

class InitiateCheckoutRequest(BaseModel):
    """Optional request body for InitiateCheckout tracking with plan details."""
    value: Optional[float] = None  # Plan price in dollars
    currency: Optional[str] = "USD"
    content_id: Optional[str] = None  # Plan name/ID
    content_name: Optional[str] = None  # Plan display name
    content_type: Optional[str] = "subscription"  # Default to subscription for SaaS

@router.post("/track-initiate-checkout")
async def track_initiate_checkout(
    request: Request,
    body: Optional[InitiateCheckoutRequest] = None,
    current_user: Optional[UserProfile] = Depends(get_current_user_optional),
):
    """Track InitiateCheckout event for Facebook and TikTok Conversions API.
    
    Note: Authentication is optional - we track for both authenticated and anonymous users.
    
    Optional body parameters allow tracking the specific plan value when user selects a plan.
    This helps optimize ad delivery for high-value conversions.
    """
    # Log comprehensive request details to debug auto-triggering
    try:
        referer = request.headers.get("referer")
        user_agent = request.headers.get("user-agent")
        origin = request.headers.get("origin")
        
        logger.info(f"🛒 INITIATE_CHECKOUT: IP={request.client.host if request.client else 'unknown'}")
        logger.info(f"   User: {current_user.email if current_user else 'anonymous'}")
        if body and body.value:
            logger.info(f"   Value: {body.currency} {body.value}")
            logger.info(f"   Plan: {body.content_name or body.content_id or 'unknown'}")
    except Exception as e:
        logger.warning(f"Failed to log InitiateCheckout request details: {e}")

    try:
        from app.services.facebook_conversions import FacebookConversionsService
        from app.services.tiktok_conversions import TikTokConversionsService
        from app.services.ga4_service import GA4Service
        
        # Get client IP and user agent
        client_ip = get_client_ip(request)
        client_user_agent = request.headers.get("user-agent")
        
        # Get Facebook cookies if available
        fbp = request.cookies.get("_fbp")
        fbc = request.cookies.get("_fbc")
        
        # Get TikTok cookies if available
        ttp = request.cookies.get("_ttp")
        ttclid = request.cookies.get("_ttclid") or request.cookies.get("ttclid")
        
        # GA4 cookies
        ga_client_id = None
        ga_session_id = None
        ga_cookie = request.cookies.get("_ga")
        if ga_cookie:
            parts = ga_cookie.split('.')
            if len(parts) >= 2:
                ga_client_id = '.'.join(parts[-2:])
            else:
                ga_client_id = ga_cookie
        # Try to find session ID cookie
        for cookie_name, cookie_value in request.cookies.items():
            if cookie_name.startswith("_ga_"):
                parts = cookie_value.split(".")
                if len(parts) > 2:
                    ga_session_id = parts[2]
                    break
        
        conversions_service = FacebookConversionsService()
        tiktok_service = TikTokConversionsService()
        ga4_service = GA4Service()
        
        # Extract first and last name from display_name if available (for authenticated users)
        first_name = None
        last_name = None
        if current_user and current_user.display_name:
            name_parts = current_user.display_name.split(maxsplit=1)
            first_name = name_parts[0] if name_parts else None
            last_name = name_parts[1] if len(name_parts) > 1 else None
        
        # Extract value parameters from body (if provided)
        value = body.value if body else None
        currency = body.currency if body else "USD"
        content_ids = [body.content_id] if body and body.content_id else None
        content_name = body.content_name if body else None
        content_type = body.content_type if body else "subscription"
        
        # Track event (fire and forget)
        import asyncio
        # Facebook tracking
        asyncio.create_task(conversions_service.track_initiate_checkout(
            email=current_user.email if current_user else None,
            external_id=str(current_user.id) if current_user else None,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            fbp=fbp,
            fbc=fbc,
            event_source_url=f"{settings.FRONTEND_URL}/upgrade",
            value=value,
            currency=currency,
            content_ids=content_ids,
            content_name=content_name,
            content_type=content_type,
            num_items=1 if value else None,
        ))
        
        # TikTok tracking
        asyncio.create_task(tiktok_service.track_initiate_checkout(
            email=current_user.email if current_user else None,
            first_name=first_name,
            last_name=last_name,
            external_id=str(current_user.id) if current_user else None,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            event_source_url=f"{settings.FRONTEND_URL}/upgrade",
            ttp=ttp,
            ttclid=ttclid,
            value=value,
            currency=currency,
            content_ids=content_ids,
            content_name=content_name,
            content_type=content_type,
            num_items=1 if value else None,
        ))
        
        # GA4 tracking
        if ga_client_id:
            asyncio.create_task(ga4_service.track_begin_checkout(
                client_id=ga_client_id,
                value=value or 0,
                currency=currency,
                user_id=str(current_user.id) if current_user else None,
                session_id=ga_session_id,
                client_ip=client_ip,
                user_agent=client_user_agent,
                page_location=f"{settings.FRONTEND_URL}/upgrade",
                items=[{"item_id": content_ids[0] if content_ids else "subscription", "item_name": content_name or "Subscription", "price": value or 0, "quantity": 1}] if content_ids or content_name else None
            ))
        
        return {"status": "success"}
    except Exception as e:
        logger.warning(f"Failed to track InitiateCheckout event: {str(e)}")
        return {"status": "error", "message": str(e)}

@router.post("/track-view-content")
async def track_view_content(
    request: Request,
    current_user: Optional[UserProfile] = Depends(get_current_user_optional),
):
    """Track ViewContent event for Facebook and TikTok Conversions API.
    
    Note: Authentication is optional - we track for both authenticated and anonymous users.
    """
    try:
        from app.services.facebook_conversions import FacebookConversionsService
        from app.services.tiktok_conversions import TikTokConversionsService
        from app.services.ga4_service import GA4Service
        
        # Get client IP and user agent
        client_ip = get_client_ip(request)
        client_user_agent = request.headers.get("user-agent")
        
        # Get Facebook cookies if available
        fbp = request.cookies.get("_fbp")
        fbc = request.cookies.get("_fbc")
        
        # Get TikTok cookies if available
        ttp = request.cookies.get("_ttp")
        ttclid = request.cookies.get("_ttclid")
        
        # GA4 cookies
        ga_client_id = None
        ga_session_id = None
        ga_cookie = request.cookies.get("_ga")
        if ga_cookie:
            parts = ga_cookie.split('.')
            if len(parts) >= 2:
                ga_client_id = '.'.join(parts[-2:])
            else:
                ga_client_id = ga_cookie
        for cookie_name, cookie_value in request.cookies.items():
            if cookie_name.startswith("_ga_"):
                parts = cookie_value.split(".")
                if len(parts) > 2:
                    ga_session_id = parts[2]
                    break
        
        # Get event_source_url from query params or use referer
        event_source_url = request.query_params.get("url") or request.headers.get("referer") or f"{settings.FRONTEND_URL}/"
        
        logger.info(f"ViewContent tracking request - URL: {event_source_url}, User: {current_user.id if current_user else 'anonymous'}")
        
        conversions_service = FacebookConversionsService()
        tiktok_service = TikTokConversionsService()
        ga4_service = GA4Service()
        
        # Track event (fire and forget)
        import asyncio
        # Facebook tracking
        asyncio.create_task(conversions_service.track_view_content(
            email=current_user.email if current_user else None,
            external_id=str(current_user.id) if current_user else None,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            fbp=fbp,
            fbc=fbc,
            event_source_url=event_source_url,
        ))
        
        # TikTok tracking
        asyncio.create_task(tiktok_service.track_view_content(
            email=current_user.email if current_user else None,
            external_id=str(current_user.id) if current_user else None,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            event_source_url=event_source_url,
            ttp=ttp,
            ttclid=ttclid,
        ))
        
        # GA4 tracking
        if ga_client_id:
            asyncio.create_task(ga4_service.track_view_item(
                client_id=ga_client_id,
                value=0,
                currency="USD",
                user_id=str(current_user.id) if current_user else None,
                session_id=ga_session_id,
                client_ip=client_ip,
                user_agent=client_user_agent,
                page_location=event_source_url,
                items=[{"item_id": "ruxo_subscription", "item_name": "Ruxo Subscription", "price": 0, "quantity": 1}]
            ))
        
        logger.info(f"Triggered ViewContent event tracking for URL: {event_source_url}")
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to track ViewContent event: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

@router.post("/track-add-to-cart")
async def track_add_to_cart(
    request: Request,
    current_user: Optional[UserProfile] = Depends(get_current_user_optional),
):
    """Track AddToCart event for Facebook Conversions API.
    
    Note: Authentication is optional - we track for both authenticated and anonymous users.
    """
    try:
        from app.services.facebook_conversions import FacebookConversionsService
        from app.services.tiktok_conversions import TikTokConversionsService
        from app.services.ga4_service import GA4Service
        
        # Get client IP and user agent
        client_ip = get_client_ip(request)
        client_user_agent = request.headers.get("user-agent")
        
        # Get fbp and fbc cookies if available
        fbp = request.cookies.get("_fbp")
        fbc = request.cookies.get("_fbc")
        
        # Get TikTok cookies if available
        ttp = request.cookies.get("_ttp")
        ttclid = request.cookies.get("_ttclid") or request.cookies.get("ttclid")
        
        # GA4 cookies
        ga_client_id = None
        ga_session_id = None
        ga_cookie = request.cookies.get("_ga")
        if ga_cookie:
            parts = ga_cookie.split('.')
            if len(parts) >= 2:
                ga_client_id = '.'.join(parts[-2:])
            else:
                ga_client_id = ga_cookie
        for cookie_name, cookie_value in request.cookies.items():
            if cookie_name.startswith("_ga_"):
                parts = cookie_value.split(".")
                if len(parts) > 2:
                    ga_session_id = parts[2]
                    break
        
        # Get event_source_url from query params or use referer
        event_source_url = request.query_params.get("url") or request.headers.get("referer") or f"{settings.FRONTEND_URL}/upgrade"
        
        logger.info(f"AddToCart tracking request - URL: {event_source_url}, User: {current_user.id if current_user else 'anonymous'}")
        
        conversions_service = FacebookConversionsService()
        tiktok_service = TikTokConversionsService()
        ga4_service = GA4Service()
        
        # Extract first and last name from display_name if available (for authenticated users)
        first_name = None
        last_name = None
        if current_user and current_user.display_name:
            name_parts = current_user.display_name.split(maxsplit=1)
            first_name = name_parts[0] if name_parts else None
            last_name = name_parts[1] if len(name_parts) > 1 else None
        
        # Generate event_id for deduplication
        import time
        # Use 5-second window for deduplication to handle rapid-fire requests (double clicks, etc.)
        # This groups requests happening within the same 5s window into the same event ID
        time_window = int(time.time()) // 5
        event_id = f"addtocart_{time_window}_{current_user.id if current_user else 'anonymous'}"
        
        # Track event (fire and forget)
        import asyncio
        # Facebook tracking
        asyncio.create_task(conversions_service.track_add_to_cart(
            currency="USD",
            value=None,  # Optional - we don't know which plan they'll select yet
            content_ids=["ruxo_subscription"],  # SaaS subscription identifier
            content_name="Ruxo Subscription Plan",  # SaaS-specific content name
            content_type="subscription",  # SaaS subscription type (not "product")
            contents=None,  # Optional - can be set if we have specific plan details
            num_items=1,  # User is viewing subscription plans
            email=current_user.email if current_user else None,
            first_name=first_name,  # Include user's first name
            last_name=last_name,  # Include user's last name
            external_id=str(current_user.id) if current_user else None,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            fbp=fbp,
            fbc=fbc,
            event_source_url=event_source_url,
            event_id=event_id,
        ))
        
        # TikTok tracking
        asyncio.create_task(tiktok_service.track_add_to_cart(
            currency="USD",
            value=None,  # Optional - we don't know which plan they'll select yet
            content_ids=["ruxo_subscription"],  # SaaS subscription identifier
            content_name="Ruxo Subscription Plan",  # SaaS-specific content name
            content_type="subscription",  # SaaS subscription type (not "product")
            contents=None,  # Optional - can be set if we have specific plan details
            num_items=1,  # User is viewing subscription plans
            email=current_user.email if current_user else None,
            first_name=first_name,  # Include user's first name
            last_name=last_name,  # Include user's last name
            external_id=str(current_user.id) if current_user else None,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            event_source_url=event_source_url,
            event_id=event_id,
            ttp=ttp,  # TikTok cookie for attribution
            ttclid=ttclid,  # TikTok click ID for ad attribution
        ))
        
        # GA4 tracking
        if ga_client_id:
            asyncio.create_task(ga4_service.track_add_to_cart(
                client_id=ga_client_id,
                value=0,
                currency="USD",
                user_id=str(current_user.id) if current_user else None,
                session_id=ga_session_id,
                client_ip=client_ip,
                user_agent=client_user_agent,
                page_location=event_source_url,
                items=[{"item_id": "ruxo_subscription", "item_name": "Ruxo Subscription Plan", "price": 0, "quantity": 1}]
            ))
        
        logger.info(f"Triggered AddToCart event tracking for URL: {event_source_url}")
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to track AddToCart event: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

@router.post("/test-purchase")
async def test_purchase(
    request: Request,
    current_user: UserProfile = Depends(get_current_user),
):
    """Test endpoint to verify Purchase event tracking (for testing only)."""
    try:
        from app.services.facebook_conversions import FacebookConversionsService
        
        # Get client IP and user agent
        client_ip = get_client_ip(request)
        client_user_agent = request.headers.get("user-agent")
        
        # Get fbp and fbc cookies if available
        fbp = request.cookies.get("_fbp")
        fbc = request.cookies.get("_fbc")
        
        conversions_service = FacebookConversionsService()
        
        # Test with a sample purchase value
        test_value = 29.99  # Example: $29.99
        test_event_id = f"test_{int(time.time())}_{current_user.id}"  # Unique test event ID
        
        # Track purchase (fire and forget)
        import asyncio
        result = await conversions_service.track_purchase(
            value=test_value,
            currency="USD",
            email=current_user.email,
            external_id=str(current_user.id),
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            fbp=fbp,
            fbc=fbc,
            event_source_url=f"{settings.FRONTEND_URL}/upgrade",
            event_id=test_event_id,
        )
        
        if result:
            return {"status": "success", "message": "Purchase event sent successfully", "value": test_value, "event_id": test_event_id}
        else:
            return {"status": "error", "message": "Failed to send Purchase event"}
    except Exception as e:
        logger.error(f"Failed to test Purchase event: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

@router.post("/sync-subscription")
async def sync_subscription(
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Manually sync subscription status from Stripe.
    Useful if webhooks fail or are delayed.
    """
    try:
        import stripe
        
        # Find customer ID
        customer_id = current_user.stripe_customer_id
        if not customer_id:
            # Try to find by email
            customers = stripe.Customer.list(email=current_user.email, limit=1)
            if customers.data:
                customer_id = customers.data[0].id
                # Update user
                current_user.stripe_customer_id = customer_id
                session.add(current_user)
                await session.commit()
        
        if not customer_id:
             return {"status": "no_customer", "message": "No Stripe customer found"}

        # Get subscriptions
        subscriptions = stripe.Subscription.list(
            customer=customer_id, 
            status="all", 
            limit=5
        )
        
        active_or_trialing = [s for s in subscriptions.data if s.status in ["active", "trialing"]]
        
        if not active_or_trialing:
            # No active subscriptions
            return {"status": "no_subscription", "message": "No active or trialing subscriptions found in Stripe"}
            
        # Process each active/trialing subscription
        service = BillingService(session)
        synced_count = 0
        for sub in active_or_trialing:
            await service._process_subscription(sub, current_user.id)
            synced_count += 1
            
        return {"status": "success", "message": f"Synced {synced_count} subscription(s)", "synced_count": synced_count}
        
    except Exception as e:
        logger.error(f"Failed to sync subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/skip-trial-and-subscribe")
async def skip_trial_and_subscribe(
    request: Request,
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Skip the trial period and subscribe to the full plan immediately.
    
    This endpoint:
    1. Finds the user's active trial subscription
    2. Gets the plan they selected from Stripe subscription metadata
    3. Creates a checkout session with skip_trial=true for that plan
    4. Returns the checkout URL - when user completes checkout, old trial will be cancelled
    """
    try:
        import stripe
        from app.models.billing import Subscription, Plan
        
        # Find user's trial subscription
        result = await session.execute(
            select(Subscription).where(
                Subscription.user_id == current_user.id,
                Subscription.status.in_(["trialing", "active"])
            )
        )
        subscriptions = result.scalars().all()
        
        # Find a trial subscription
        trial_subscription = None
        for sub in subscriptions:
            if sub.status == "trialing":
                trial_subscription = sub
                break
            elif sub.plan_name and ("trial" in sub.plan_name.lower() or sub.plan_name.lower() == "free_trial"):
                trial_subscription = sub
                break
        
        if not trial_subscription:
            logger.info(f"No trial subscription found in DB for user {current_user.id}. Checking Stripe directly...")
            
            # Fallback: Check Stripe directly for active subscriptions
            try:
                customers = stripe.Customer.list(email=current_user.email, limit=1)
                if customers.data:
                    customer_id = customers.data[0].id
                    subs = stripe.Subscription.list(customer=customer_id, status="trialing", limit=1)
                    if not subs.data:
                        subs = stripe.Subscription.list(customer=customer_id, status="active", limit=1)
                    
                    if subs.data:
                        stripe_sub = subs.data[0]
                        logger.info(f"Found subscription in Stripe: {stripe_sub.id}")
                        
                        class TempSub:
                            stripe_subscription_id = stripe_sub.id
                        trial_subscription = TempSub()
            except Exception as e:
                logger.error(f"Error checking Stripe directly: {e}")

        if not trial_subscription:
            logger.info(f"No trial subscription found anywhere for user {current_user.id}")
            raise HTTPException(
                status_code=400, 
                detail="You don't have an active trial subscription. Please start a trial first."
            )
        
        logger.info(f"Using subscription ID: {trial_subscription.stripe_subscription_id}")
        
        # Get the subscription from Stripe to find the actual plan
        try:
            stripe_sub = stripe.Subscription.retrieve(trial_subscription.stripe_subscription_id)
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve Stripe subscription: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve subscription from Stripe. Please try again."
            )
        
        # Get the actual plan name from subscription metadata
        actual_plan_name = stripe_sub.metadata.get("plan_name")
        
        if not actual_plan_name:
            # Fallback: Get from price ID
            if not stripe_sub.items.data:
                raise HTTPException(
                    status_code=500,
                    detail="Subscription has no items. Please contact support."
                )
            
            price_id = stripe_sub.items.data[0].price.id
            
            plan_result = await session.execute(
                select(Plan).where(
                    Plan.stripe_price_id == price_id,
                    Plan.name != "free_trial"
                )
            )
            plan = plan_result.scalar_one_or_none()
            if plan:
                actual_plan_name = plan.name
        
        if not actual_plan_name:
            raise HTTPException(
                status_code=404,
                detail="Could not find the plan for your subscription. Please contact support."
            )
        
        # Get tracking context
        client_ip = get_client_ip(request)
        client_user_agent = request.headers.get("user-agent")
        fbp = request.cookies.get("_fbp")
        fbc = request.cookies.get("_fbc")
        ttp = request.cookies.get("_ttp")
        ttclid = request.cookies.get("_ttclid") or request.cookies.get("ttclid")
        
        # GA4 cookies
        ga_client_id = None
        ga_session_id = None
        ga_cookie = request.cookies.get("_ga")
        if ga_cookie:
            parts = ga_cookie.split('.')
            if len(parts) >= 2:
                ga_client_id = '.'.join(parts[-2:])
            else:
                ga_client_id = ga_cookie
        # Try to find session ID cookie
        for cookie_name, cookie_value in request.cookies.items():
            if cookie_name.startswith("_ga_"):
                parts = cookie_value.split(".")
                if len(parts) > 2:
                    ga_session_id = parts[2]
                    break
        
        # Create checkout session with skip_trial=true
        service = BillingService(session)
        url = await service.create_checkout_session(
            user=current_user,
            plan_name=actual_plan_name,
            skip_trial=True,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            fbp=fbp,
            fbc=fbc,
            ttp=ttp,
            ttclid=ttclid,
            ga_client_id=ga_client_id,
            ga_session_id=ga_session_id,
        )
        
        logger.info(f"Created skip-trial checkout for user {current_user.id}, plan {actual_plan_name}")
        
        return {
            "status": "success",
            "url": url,
            "plan_name": actual_plan_name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create skip-trial checkout for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create checkout: {str(e)}")

