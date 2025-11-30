
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
from app.models.billing import Plan
from app.models.credits import CreditWallet, CreditTransaction
from app.models.user import UserProfile

# Database URL from .env
DATABASE_URL = "postgresql+asyncpg://postgres:KSu1wZsobckLwdhu@db.cutgibszjdnxsrlclbos.supabase.co:5432/postgres"

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

USER_ID = "53f7bdca-33ba-4a77-9d8a-d817fac0cf45"
PLAN_NAME = "starter_yearly"
NEW_TRIAL_CREDITS = 200

async def fix_trial():
    async with async_session_maker() as session:
        # 1. Update Plan Trial Credits
        result = await session.exec(select(Plan).where(Plan.name == PLAN_NAME))
        plan = result.first()
        if plan:
            print(f"Updating plan {plan.name} trial credits from {plan.trial_credits} to {NEW_TRIAL_CREDITS}...")
            plan.trial_credits = NEW_TRIAL_CREDITS
            session.add(plan)
        else:
            print(f"Plan {PLAN_NAME} not found!")
            return

        # 2. Update User Credits
        user_uuid = uuid.UUID(USER_ID)
        result = await session.exec(select(CreditWallet).where(CreditWallet.user_id == user_uuid))
        wallet = result.first()
        
        if wallet:
            # Calculate difference to add
            # We want them to have roughly the trial amount minus what they spent
            # Or just top them up to a usable amount.
            # Let's just add the difference between new trial credits and old trial credits (200 - 70 = 130)
            # So they get the "full" trial experience
            
            credits_to_add = NEW_TRIAL_CREDITS - 70 
            if credits_to_add > 0:
                print(f"Adding {credits_to_add} credits to user wallet (Current: {wallet.balance_credits})...")
                wallet.balance_credits += credits_to_add
                wallet.lifetime_credits_added += credits_to_add
                session.add(wallet)
                
                # Record transaction
                transaction = CreditTransaction(
                    user_id=user_uuid,
                    amount=credits_to_add,
                    direction="credit",
                    reason="trial_adjustment",
                    metadata_json='{"note": "Updated trial credits to 200"}'
                )
                session.add(transaction)
        
        await session.commit()
        print("✅ Trial updated successfully!")

if __name__ == "__main__":
    asyncio.run(fix_trial())

