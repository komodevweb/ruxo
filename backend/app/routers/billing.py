from fastapi import APIRouter, Depends, HTTPException, Response, Request
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
    fbp = request.cookies.get("_fbp")
    fbc = request.cookies.get("_fbc")
    
    logger.info(f"💳 [CHECKOUT] Creating checkout session for user {current_user.id}")
    logger.info(f"💳 [CHECKOUT] Captured tracking context: IP={client_ip}, UA={client_user_agent[:50] if client_user_agent else 'None'}..., fbp={fbp}, fbc={fbc}")
    
    service = BillingService(session)
    url = await service.create_checkout_session(
        user=current_user,
        plan_name=data.plan_name,
        client_ip=client_ip,
        client_user_agent=client_user_agent,
        fbp=fbp,
        fbc=fbc
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
    
    cache_key_str = cache_key("cache", "billing", "plans")
    
    # Try Redis cache first
    cached = await get_cached(cache_key_str)
    if cached is not None:
        if response:
            response.headers["Cache-Control"] = "public, max-age=300"  # 5 min browser cache
            response.headers["X-Cache"] = "HIT"
        return cached
    
    # Cache miss - fetch from database
    result = await session.execute(
        select(Plan).where(Plan.is_active == True).order_by(Plan.amount_cents)
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
        
        plans_data.append({
            "id": str(plan.id),
            "name": plan.name,
            "display_name": plan.display_name,
            "amount_cents": amount_cents,
            "amount_dollars": amount_dollars,
            "original_amount_cents": original_amount_cents,
            "original_amount_dollars": original_amount_dollars,
            "interval": plan.interval,
            "credits_per_month": plan.credits_per_month,
            "currency": plan.currency,
        })
    
    # Cache in Redis for 1 hour
    await set_cached(cache_key_str, plans_data, ttl=3600)
    
    # Set cache headers
    if response:
        response.headers["Cache-Control"] = "public, max-age=300"  # 5 min browser cache
        response.headers["X-Cache"] = "MISS"
    
    return plans_data

@router.post("/track-initiate-checkout")
async def track_initiate_checkout(
    request: Request,
    current_user: Optional[UserProfile] = Depends(get_current_user_optional),
):
    """Track InitiateCheckout event for Facebook Conversions API.
    
    Note: Authentication is optional - we track for both authenticated and anonymous users.
    """
    # Log comprehensive request details to debug auto-triggering
    try:
        referer = request.headers.get("referer")
        user_agent = request.headers.get("user-agent")
        origin = request.headers.get("origin")
        all_headers = dict(request.headers)
        
        logger.warning(f"⚠️ INITIATE_CHECKOUT_TRIGGERED: IP={request.client.host if request.client else 'unknown'}")
        logger.warning(f"   Referer: {referer}")
        logger.warning(f"   Origin: {origin}")
        logger.warning(f"   User-Agent: {user_agent}")
        logger.warning(f"   User: {current_user.email if current_user else 'anonymous'}")
        logger.warning(f"   All Headers: {all_headers}")
    except Exception as e:
        logger.warning(f"Failed to log InitiateCheckout request details: {e}")

    try:
        from app.services.facebook_conversions import FacebookConversionsService
        
        # Get client IP and user agent
        client_ip = get_client_ip(request)
        client_user_agent = request.headers.get("user-agent")
        
        # Get fbp and fbc cookies if available
        fbp = request.cookies.get("_fbp")
        fbc = request.cookies.get("_fbc")
        
        conversions_service = FacebookConversionsService()
        
        # Track event (fire and forget)
        import asyncio
        asyncio.create_task(conversions_service.track_initiate_checkout(
            email=current_user.email if current_user else None,
            external_id=str(current_user.id) if current_user else None,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            fbp=fbp,
            fbc=fbc,
            event_source_url=f"{settings.FRONTEND_URL}/upgrade",
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
    """Track ViewContent event for Facebook Conversions API.
    
    Note: Authentication is optional - we track for both authenticated and anonymous users.
    """
    try:
        from app.services.facebook_conversions import FacebookConversionsService
        
        # Get client IP and user agent
        client_ip = get_client_ip(request)
        client_user_agent = request.headers.get("user-agent")
        
        # Get fbp and fbc cookies if available
        fbp = request.cookies.get("_fbp")
        fbc = request.cookies.get("_fbc")
        
        # Get event_source_url from query params or use referer
        event_source_url = request.query_params.get("url") or request.headers.get("referer") or f"{settings.FRONTEND_URL}/"
        
        logger.info(f"ViewContent tracking request - URL: {event_source_url}, User: {current_user.id if current_user else 'anonymous'}")
        
        conversions_service = FacebookConversionsService()
        
        # Track event (fire and forget)
        import asyncio
        asyncio.create_task(conversions_service.track_view_content(
            email=current_user.email if current_user else None,
            external_id=str(current_user.id) if current_user else None,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            fbp=fbp,
            fbc=fbc,
            event_source_url=event_source_url,
        ))
        
        logger.info(f"Triggered ViewContent event tracking for URL: {event_source_url}")
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to track ViewContent event: {str(e)}", exc_info=True)
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

