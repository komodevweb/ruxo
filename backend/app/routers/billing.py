from fastapi import APIRouter, Depends, HTTPException, Response
from datetime import datetime
from typing import Optional, Dict, Any, List
from app.schemas.billing import CheckoutSessionCreate, CheckoutSessionResponse, PortalSessionResponse
from app.core.security import get_current_user
from app.models.user import UserProfile
from app.models.billing import Plan
from app.services.billing_service import BillingService
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter()

# Simple in-memory cache for plans
_plans_cache: Optional[List[Dict[str, Any]]] = None
_cache_timestamp: Optional[datetime] = None
CACHE_TTL_SECONDS = 3600  # 1 hour (plans don't change often)

def invalidate_plans_cache():
    """Invalidate the plans cache (call this when plans are updated)."""
    global _plans_cache, _cache_timestamp
    _plans_cache = None
    _cache_timestamp = None

@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    data: CheckoutSessionCreate,
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    service = BillingService(session)
    url = await service.create_checkout_session(current_user, data.plan_name)
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
    """Get all active subscription plans (cached for 1 hour)."""
    global _plans_cache, _cache_timestamp
    
    # Check if cache is valid
    now = datetime.utcnow()
    if _plans_cache is not None and _cache_timestamp is not None:
        if (now - _cache_timestamp).total_seconds() < CACHE_TTL_SECONDS:
            # Set cache headers for browser caching
            if response:
                response.headers["Cache-Control"] = "public, max-age=300"  # 5 min browser cache
                response.headers["X-Cache"] = "HIT"
            return _plans_cache
    
    # Fetch from database (optimized query - only select needed columns)
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
    
    # Update cache
    _plans_cache = plans_data
    _cache_timestamp = now
    
    # Set cache headers
    if response:
        response.headers["Cache-Control"] = "public, max-age=300"  # 5 min browser cache
        response.headers["X-Cache"] = "MISS"
    
    return plans_data

