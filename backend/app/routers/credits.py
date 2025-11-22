from fastapi import APIRouter, Depends
from app.schemas.credits import CreditBalance
from app.core.security import get_current_user
from app.models.user import UserProfile
from app.services.credits_service import CreditsService
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("/me", response_model=CreditBalance)
async def get_credits(
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    service = CreditsService(session)
    wallet = await service.get_wallet(current_user.id)
    return CreditBalance(
        balance=wallet.balance_credits,
        lifetime_used=wallet.lifetime_credits_spent,
        last_updated=wallet.updated_at
    )

