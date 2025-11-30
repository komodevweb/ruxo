
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
from app.models.credits import CreditWallet
from app.models.user import UserProfile

# Database URL from .env
DATABASE_URL = "postgresql+asyncpg://postgres:KSu1wZsobckLwdhu@db.cutgibszjdnxsrlclbos.supabase.co:5432/postgres"

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

USER_ID = "53f7bdca-33ba-4a77-9d8a-d817fac0cf45"

async def check_credits():
    async with async_session_maker() as session:
        user_uuid = uuid.UUID(USER_ID)
        
        # Get User
        user = await session.get(UserProfile, user_uuid)
        print(f"User: {user.email}")
        
        # Get Wallet
        result = await session.exec(select(CreditWallet).where(CreditWallet.user_id == user_uuid))
        wallet = result.first()
        
        if wallet:
            print(f"Credit Balance: {wallet.balance_credits}")
            print(f"Lifetime Added: {wallet.lifetime_credits_added}")
            print(f"Lifetime Spent: {wallet.lifetime_credits_spent}")
        else:
            print("No credit wallet found.")

if __name__ == "__main__":
    asyncio.run(check_credits())

