import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.billing import Plan, Subscription
from app.models.user import UserProfile
from app.services.credits_service import CreditsService
from sqlalchemy.future import select

async def set_user_plan(user_email: str, plan_name: str):
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        # Find user
        result = await session.execute(
            select(UserProfile).where(UserProfile.email == user_email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"User not found: {user_email}")
            return
        
        print(f"Found user: {user.email} (ID: {user.id})")
        
        # Find plan
        result = await session.execute(
            select(Plan).where(Plan.name == plan_name)
        )
        plan = result.scalar_one_or_none()
        
        if not plan:
            print(f"Plan not found: {plan_name}")
            return
            
        print(f"Found plan: {plan.name} (ID: {plan.id})")
        
        # Check existing subscription
        result = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.status.in_(["active", "trialing"])
            )
        )
        subscription = result.scalar_one_or_none()
        
        now = datetime.utcnow()
        
        if subscription:
            print(f"Updating existing subscription {subscription.id}...")
            subscription.plan_id = plan.id
            subscription.plan_name = plan.name
            subscription.status = "trialing"
            subscription.updated_at = now
            session.add(subscription)
        else:
            print("Creating new subscription...")
            subscription = Subscription(
                user_id=user.id,
                plan_id=plan.id,
                plan_name=plan.name,
                stripe_customer_id="manual_fix",
                stripe_subscription_id=f"sub_manual_{int(now.timestamp())}",
                status="trialing",
                current_period_start=now,
                current_period_end=now + timedelta(days=3),
                created_at=now,
                updated_at=now
            )
            session.add(subscription)
            
        await session.commit()
        
        # Grant credits
        credits_service = CreditsService(session)
        wallet = await credits_service.get_wallet(user.id)
        
        # Set balance to trial credits (40)
        wallet.balance_credits = 40
        session.add(wallet)
        await session.commit()
        
        print(f"✅ Successfully set plan to {plan.name} and credits to 40 for {user.email}")
        
        # Invalidate cache
        from app.utils.cache import invalidate_user_cache
        await invalidate_user_cache(str(user.id))
        print("✅ Cache invalidated")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/set_user_plan.py <user_email> <plan_name>")
        sys.exit(1)
    
    user_email = sys.argv[1]
    plan_name = sys.argv[2]
    asyncio.run(set_user_plan(user_email, plan_name))
