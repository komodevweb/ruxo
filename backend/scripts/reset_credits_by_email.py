import asyncio
import sys
import os
from pathlib import Path
import argparse

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.session import engine
from app.models.user import UserProfile
from app.models.billing import Subscription, Plan
from app.models.credits import CreditWallet, CreditTransaction
from sqlalchemy.ext.asyncio import AsyncSession as AsyncSessionType
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

async def reset_credits_by_email(email: str):
    """Reset credits for a user by email based on their active subscription."""
    async_session = sessionmaker(engine, class_=AsyncSessionType, expire_on_commit=False)
    async with async_session() as session:
        try:
            # Find user by email
            print(f"🔍 Looking for user with email: {email}")
            result = await session.execute(
                select(UserProfile).where(UserProfile.email == email)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"❌ User not found with email: {email}")
                return
            
            print(f"✅ Found user: {user.id}")
            
            # Find active subscription
            result = await session.execute(
                select(Subscription).where(
                    Subscription.user_id == user.id,
                    Subscription.status == "active"
                ).order_by(Subscription.created_at.desc())
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                print(f"❌ No active subscription found for user")
                # Check if they have any subscription just in case
                result = await session.execute(
                    select(Subscription).where(
                        Subscription.user_id == user.id
                    ).order_by(Subscription.created_at.desc())
                )
                last_sub = result.scalar_one_or_none()
                if last_sub:
                    print(f"   Found inactive subscription: {last_sub.status} (ID: {last_sub.id})")
                return
            
            print(f"✅ Found active subscription: {subscription.id} (Plan ID: {subscription.plan_id})")
            
            # Get plan
            result = await session.execute(
                select(Plan).where(Plan.id == subscription.plan_id)
            )
            plan = result.scalar_one_or_none()
            
            if not plan:
                print(f"❌ Plan not found for subscription")
                return
            
            print(f"✅ Plan: {plan.display_name} ({plan.name})")
            print(f"   Target Credits: {plan.credits_per_month}")
            
            # Get wallet
            result = await session.execute(
                select(CreditWallet).where(CreditWallet.user_id == user.id)
            )
            wallet = result.scalar_one_or_none()
            
            if not wallet:
                print("❌ Wallet not found, creating one...")
                wallet = CreditWallet(user_id=user.id, balance_credits=0)
                session.add(wallet)
                await session.flush()
            
            old_balance = wallet.balance_credits
            target_balance = plan.credits_per_month
            
            if old_balance == target_balance:
                print(f"ℹ️  User already has correct balance: {old_balance}")
                return

            print(f"🔄 Resetting balance from {old_balance} to {target_balance}")
            
            # Update wallet
            wallet.balance_credits = target_balance
            
            # Record transaction
            transaction = CreditTransaction(
                user_id=user.id,
                amount=target_balance - old_balance,
                direction="credit" if target_balance > old_balance else "debit",
                reason="manual_reset",
                metadata_json=f'{{"reason": "support_request", "admin_reset": true, "old_balance": {old_balance}, "new_balance": {target_balance}}}'
            )
            session.add(transaction)
            session.add(wallet)
            await session.commit()
            
            print(f"✅ Successfully reset credits for {email}")
            print(f"   New Balance: {wallet.balance_credits}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python reset_credits_by_email.py <email>")
        sys.exit(1)
    
    email = sys.argv[1]
    asyncio.run(reset_credits_by_email(email))

