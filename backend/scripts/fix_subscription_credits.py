"""
Script to manually check and fix subscription credits.

This can be used to:
1. Check if a user has a subscription but no credits
2. Manually add credits for a subscription
3. Debug subscription/credit issues

Usage:
    python scripts/fix_subscription_credits.py <user_email>
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import AsyncSession as AsyncSessionType
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import engine
from app.models.billing import Subscription, Plan
from app.models.user import UserProfile
from app.services.credits_service import CreditsService
from app.services.billing_service import BillingService

async def fix_user_credits(email: str):
    """Check and fix credits for a user."""
    async_session = sessionmaker(engine, class_=AsyncSessionType, expire_on_commit=False)
    async with async_session() as session:
        try:
            # Find user
            result = await session.execute(
                select(UserProfile).where(UserProfile.email == email)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"User with email {email} not found")
                return
            
            print(f"Found user: {user.email} (ID: {user.id})")
            
            # Find active subscription
            result = await session.execute(
                select(Subscription).where(
                    Subscription.user_id == user.id,
                    Subscription.status == "active"
                )
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                print("No active subscription found for this user")
                return
            
            print(f"Found subscription: {subscription.plan_name} (Status: {subscription.status})")
            
            # Get plan
            if not subscription.plan_id:
                print("Subscription has no plan_id")
                return
            
            result = await session.execute(
                select(Plan).where(Plan.id == subscription.plan_id)
            )
            plan = result.scalar_one_or_none()
            
            if not plan:
                print(f"Plan not found for plan_id {subscription.plan_id}")
                return
            
            print(f"Plan: {plan.name} - {plan.credits_per_month} credits/month")
            
            # Get current wallet
            credits_service = CreditsService(session)
            wallet = await credits_service.get_wallet(user.id)
            
            print(f"Current credit balance: {wallet.balance_credits}")
            print(f"Expected credits: {plan.credits_per_month}")
            
            if wallet.balance_credits != plan.credits_per_month:
                print(f"\nCredits mismatch! Resetting to {plan.credits_per_month}...")
                
                billing_service = BillingService(session)
                await billing_service._reset_monthly_credits(subscription)
                
                # Refresh wallet
                await session.refresh(wallet)
                print(f"New credit balance: {wallet.balance_credits}")
                print("✓ Credits fixed!")
            else:
                print("✓ Credits are correct")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/fix_subscription_credits.py <user_email>")
        sys.exit(1)
    
    email = sys.argv[1]
    print(f"Checking credits for user: {email}\n")
    asyncio.run(fix_user_credits(email))

