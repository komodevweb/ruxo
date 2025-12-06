
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
from app.models.user import UserProfile

# Database URL from .env
DATABASE_URL = "postgresql+asyncpg://postgres:KSu1wZsobckLwdhu@db.cutgibszjdnxsrlclbos.supabase.co:5432/postgres"

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

USER_EMAIL = "iphonekomo@gmail.com"
CREDITS_TO_ADD = 2000  # Add 2000 credits

async def reset_credits():
    async with async_session_maker() as session:
        # Find user by email
        result = await session.exec(select(UserProfile).where(UserProfile.email == USER_EMAIL))
        user = result.first()
        
        if not user:
            print(f"❌ User with email {USER_EMAIL} not found!")
            return
        
        print(f"✓ Found user: {user.email} (ID: {user.id})")
        
        # Get Wallet
        result = await session.exec(select(CreditWallet).where(CreditWallet.user_id == user.id))
        wallet = result.first()
        
        if wallet:
            old_balance = wallet.balance_credits
            print(f"Current Balance: {old_balance} credits")
            
            # Add credits to wallet
            wallet.balance_credits += CREDITS_TO_ADD
            wallet.lifetime_credits_added += CREDITS_TO_ADD
            session.add(wallet)
            
            # Record transaction
            transaction = CreditTransaction(
                user_id=user.id,
                amount=CREDITS_TO_ADD,
                direction="credit",
                reason="manual_grant",
                metadata_json='{"note": "Manual credit addition by admin"}'
            )
            session.add(transaction)
            
            await session.commit()
            print(f"✅ Credits added successfully!")
            print(f"   Old Balance: {old_balance} credits")
            print(f"   New Balance: {wallet.balance_credits} credits")
            print(f"   Added: {CREDITS_TO_ADD} credits")
        else:
            print("❌ No credit wallet found for this user.")

if __name__ == "__main__":
    asyncio.run(reset_credits())

