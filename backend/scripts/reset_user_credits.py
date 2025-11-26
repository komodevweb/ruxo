"""
Script to reset a user's credits to their plan amount.

Usage:
    python scripts/reset_user_credits.py <user_id>
    
Example:
    python scripts/reset_user_credits.py c31811c5-846c-4526-b726-d1dd88c13224
"""

import asyncio
import sys
import uuid
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession as AsyncSessionType
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from app.db.session import engine
from app.models.billing import Subscription, Plan
from app.models.user import UserProfile
from app.services.billing_service import BillingService
from app.services.credits_service import CreditsService

async def reset_user_credits(user_id_str: str):
    """Reset a user's credits to their plan amount."""
    async_session = sessionmaker(engine, class_=AsyncSessionType, expire_on_commit=False)
    async with async_session() as session:
        try:
            # Parse user ID
            try:
                user_id = uuid.UUID(user_id_str)
            except ValueError:
                print(f"❌ Invalid user ID format: {user_id_str}")
                return
            
            # Find user
            result = await session.execute(
                select(UserProfile).where(UserProfile.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"❌ User not found: {user_id}")
                return
            
            print(f"✓ Found user: {user.email} ({user.id})")
            
            # Find active subscription
            result = await session.execute(
                select(Subscription).where(
                    Subscription.user_id == user.id,
                    Subscription.status == "active"
                )
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                print(f"❌ No active subscription found for user {user_id}")
                return
            
            print(f"✓ Found subscription: {subscription.stripe_subscription_id}")
            print(f"  Plan: {subscription.plan_name}")
            print(f"  Status: {subscription.status}")
            
            # Get plan details
            if not subscription.plan_id:
                print(f"❌ Subscription has no plan_id")
                return
            
            result = await session.execute(
                select(Plan).where(Plan.id == subscription.plan_id)
            )
            plan = result.scalar_one_or_none()
            
            if not plan:
                print(f"❌ Plan not found for plan_id {subscription.plan_id}")
                return
            
            print(f"✓ Found plan: {plan.display_name}")
            print(f"  Credits per month: {plan.credits_per_month}")
            
            # Get current credits
            credits_service = CreditsService(session)
            wallet = await credits_service.get_wallet(user.id)
            current_credits = wallet.balance_credits
            
            print(f"\n💰 Current credits: {current_credits}")
            print(f"   Plan credits: {plan.credits_per_month}")
            
            # Force reset credits to plan amount (even if already correct)
            print(f"\n🔄 Resetting credits to plan amount...")
            billing_service = BillingService(session)
            await billing_service._reset_monthly_credits(subscription, skip_webhook_check=True)
            
            # Refresh wallet to get updated balance
            wallet = await credits_service.get_wallet(user.id)
            
            print(f"\n{'='*80}")
            print(f"✅ Successfully reset credits!")
            print(f"{'='*80}")
            print(f"User: {user.email}")
            print(f"Plan: {plan.display_name}")
            print(f"Credits: {current_credits} → {wallet.balance_credits}")
            print(f"Subscription ID: {subscription.stripe_subscription_id}")
            print(f"{'='*80}\n")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/reset_user_credits.py <user_id>")
        print("\nExample:")
        print("  python scripts/reset_user_credits.py c31811c5-846c-4526-b726-d1dd88c13224")
        sys.exit(1)
    
    user_id = sys.argv[1]
    
    print(f"Resetting credits for user {user_id}...\n")
    
    asyncio.run(reset_user_credits(user_id))

