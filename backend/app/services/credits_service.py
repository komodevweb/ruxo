import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.credits import CreditWallet, CreditTransaction
from fastapi import HTTPException

class CreditsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_wallet(self, user_id: uuid.UUID) -> CreditWallet:
        result = await self.session.execute(select(CreditWallet).where(CreditWallet.user_id == user_id))
        wallet = result.scalar_one_or_none()
        if not wallet:
            wallet = CreditWallet(user_id=user_id)
            self.session.add(wallet)
            await self.session.commit()
            await self.session.refresh(wallet)
        return wallet

    async def add_credits(self, user_id: uuid.UUID, amount: int, reason: str, metadata: dict = None):
        wallet = await self.get_wallet(user_id)
        wallet.balance_credits += amount
        wallet.lifetime_credits_added += amount
        
        transaction = CreditTransaction(
            user_id=user_id,
            amount=amount,
            direction="credit",
            reason=reason,
            metadata_json=str(metadata) if metadata else None
        )
        self.session.add(transaction)
        self.session.add(wallet)
        await self.session.commit()
        
        # Invalidate credit cache
        from app.utils.cache import invalidate_cache, cache_key
        cache_key_str = cache_key("cache", "user", str(user_id), "credits")
        await invalidate_cache(cache_key_str)
        # Also invalidate profile cache (includes credit balance)
        profile_cache_key = cache_key("cache", "user", str(user_id), "profile")
        await invalidate_cache(profile_cache_key)
        
        return wallet

    async def spend_credits(self, user_id: uuid.UUID, amount: int, reason: str, metadata: dict = None):
        wallet = await self.get_wallet(user_id)
        if wallet.balance_credits < amount:
            raise HTTPException(status_code=402, detail="Insufficient credits")
        
        wallet.balance_credits -= amount
        wallet.lifetime_credits_spent += amount
        
        transaction = CreditTransaction(
            user_id=user_id,
            amount=amount,
            direction="debit",
            reason=reason,
            metadata_json=str(metadata) if metadata else None
        )
        self.session.add(transaction)
        self.session.add(wallet)
        await self.session.commit()
        
        # Invalidate credit cache
        from app.utils.cache import invalidate_cache, cache_key
        cache_key_str = cache_key("cache", "user", str(user_id), "credits")
        await invalidate_cache(cache_key_str)
        # Also invalidate profile cache (includes credit balance)
        profile_cache_key = cache_key("cache", "user", str(user_id), "profile")
        await invalidate_cache(profile_cache_key)
        
        return wallet

