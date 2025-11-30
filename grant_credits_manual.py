
import asyncio
import sys
import os
import uuid
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import select

# Add backend directory to path
sys.path.append(os.path.abspath("backend"))

# Import models
from app.models.credits import CreditWallet, CreditTransaction

# Database URL from .env
DATABASE_URL = "postgresql+asyncpg://postgres:KSu1wZsobckLwdhu@db.cutgibszjdnxsrlclbos.supabase.co:5432/postgres"

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

USER_ID = "53f7bdca-33ba-4a77-9d8a-d817fac0cf45"
AMOUNT = 142 # Bring balance to 200 (58 + 142 = 200)

async def grant_credits():
    async with async_session_maker() as session:
        user_uuid = uuid.UUID(USER_ID)
        
        # Get Wallet
        result = await session.exec(select(CreditWallet).where(CreditWallet.user_id == user_uuid))
        wallet = result.first()
        
        if wallet:
            print(f"Current Balance: {wallet.balance_credits}")
            wallet.balance_credits += AMOUNT
            wallet.lifetime_credits_added += AMOUNT
            session.add(wallet)
            
            # Record transaction
            transaction = CreditTransaction(
                user_id=user_uuid,
                amount=AMOUNT,
                direction="credit",
                reason="manual_grant",
                metadata_json='{"note": "Trial fix for high res generation"}'
            )
            session.add(transaction)
            
            await session.commit()
            print(f"Added {AMOUNT} credits. New Balance: {wallet.balance_credits}")
        else:
            print("No credit wallet found.")

if __name__ == "__main__":
    asyncio.run(grant_credits())

