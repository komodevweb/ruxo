from fastapi import APIRouter, Depends
from app.schemas.credits import CreditBalance
from app.core.security import get_current_user
from app.models.user import UserProfile
from app.services.credits_service import CreditsService
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.cache import get_cached, set_cached, cache_key

router = APIRouter()

@router.get("/me", response_model=CreditBalance)
async def get_credits(
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get user credit balance (cached for 30 seconds for fast UI updates)."""
    cache_key_str = cache_key("cache", "user", str(current_user.id), "credits")
    
    # Try cache first
    cached = await get_cached(cache_key_str)
    if cached is not None:
        return CreditBalance(**cached)
    
    # Cache miss - fetch from database
    service = CreditsService(session)
    wallet = await service.get_wallet(current_user.id)
    result = CreditBalance(
        balance=wallet.balance_credits,
        lifetime_used=wallet.lifetime_credits_spent,
        last_updated=wallet.updated_at
    )
    
    # Cache for 30 seconds (balance changes frequently but UI polls often)
    # Use mode='json' to serialize datetimes properly
    await set_cached(cache_key_str, result.model_dump(mode='json'), ttl=30)
    
    return result

