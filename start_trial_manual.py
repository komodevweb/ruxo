
import asyncio
import sys
import os
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import select

# Add backend directory to path
sys.path.append(os.path.abspath("backend"))

# Import models
from app.models.billing import Plan, Subscription
from app.models.user import UserProfile
from app.models.credits import CreditWallet, CreditTransaction

# Database URL from .env
DATABASE_URL = "postgresql+asyncpg://postgres:KSu1wZsobckLwdhu@db.cutgibszjdnxsrlclbos.supabase.co:5432/postgres"

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

USER_ID = "53f7bdca-33ba-4a77-9d8a-d817fac0cf45"
PLAN_NAME = "starter_yearly"

async def start_trial():
    async with async_session_maker() as session:
        # 1. Get User
        user_uuid = uuid.UUID(USER_ID)
        user = await session.get(UserProfile, user_uuid)
        if not user:
            print(f"User {USER_ID} not found.")
            return

        print(f"Found user: {user.email}")

        # 2. Get Plan
        result = await session.exec(select(Plan).where(Plan.name == PLAN_NAME))
        plan = result.first()
        if not plan:
            print(f"Plan {PLAN_NAME} not found.")
            return
        
        print(f"Found plan: {plan.display_name} (Trial Days: {plan.trial_days}, Credits: {plan.trial_credits})")

        # 3. Check/Create Subscription
        # Check if user already has a subscription
        result = await session.exec(select(Subscription).where(Subscription.user_id == user_uuid))
        subscription = result.first()

        now = datetime.utcnow()
        trial_end = now + timedelta(days=plan.trial_days)

        if subscription:
            print(f"Updating existing subscription {subscription.id} to trialing...")
            subscription.status = "trialing"
            subscription.plan_id = plan.id
            subscription.plan_name = plan.name
            subscription.current_period_start = now
            subscription.current_period_end = trial_end
            session.add(subscription)
        else:
            print("Creating new subscription...")
            # Generate dummy stripe IDs for manual trial
            dummy_cus_id = f"cus_manual_{str(uuid.uuid4())[:8]}"
            dummy_sub_id = f"sub_manual_{str(uuid.uuid4())[:8]}"
            
            subscription = Subscription(
                user_id=user_uuid,
                plan_id=plan.id,
                plan_name=plan.name,
                stripe_customer_id=dummy_cus_id,
                stripe_subscription_id=dummy_sub_id,
                status="trialing",
                current_period_start=now,
                current_period_end=trial_end
            )
            session.add(subscription)

        # 4. Add Credits
        result = await session.exec(select(CreditWallet).where(CreditWallet.user_id == user_uuid))
        wallet = result.first()

        credits_to_add = plan.trial_credits

        if not wallet:
            print("Creating credit wallet...")
            wallet = CreditWallet(
                user_id=user_uuid,
                balance_credits=credits_to_add,
                lifetime_credits_added=credits_to_add,
                lifetime_credits_spent=0
            )
            session.add(wallet)
        else:
            print(f"Adding {credits_to_add} credits to wallet (Current: {wallet.balance_credits})...")
            wallet.balance_credits += credits_to_add
            wallet.lifetime_credits_added += credits_to_add
            session.add(wallet)

        # Record transaction
        transaction = CreditTransaction(
            user_id=user_uuid,
            amount=credits_to_add,
            direction="credit",
            reason="subscription_trial_start",
            metadata_json=f'{{"plan": "{plan.name}", "manual": true}}'
        )
        session.add(transaction)

        await session.commit()
        print("✅ Trial started successfully!")
        print(f"User is now on {plan.display_name} trial until {trial_end}")
        print(f"Added {credits_to_add} credits.")

if __name__ == "__main__":
    asyncio.run(start_trial())

