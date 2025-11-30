#!/usr/bin/env python3
"""
Script to manually grant credits to a user for their subscription.
Use this if webhook processed but credits weren't granted correctly.
"""
import asyncio
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.db.session import engine
from app.models.user import UserProfile
from app.models.billing import Subscription, Plan
from app.services.credits_service import CreditsService
from sqlalchemy.ext.asyncio import AsyncSession as AsyncSessionType
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
import uuid

async def grant_credits_to_user(user_id_str: str):
    """Grant credits to user based on their active subscription."""
    async_session = sessionmaker(engine, class_=AsyncSessionType, expire_on_commit=False)
    async with async_session() as session:
        try:
            user_id = uuid.UUID(user_id_str)
            
            # Find user
            result = await session.execute(
                select(UserProfile).where(UserProfile.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"❌ User not found: {user_id}")
                return
            
            print(f"✅ Found user: {user.email}")
            
            # Find active subscription
            result = await session.execute(
                select(Subscription).where(
                    Subscription.user_id == user_id,
                    Subscription.status == "active"
                ).order_by(Subscription.created_at.desc())
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                print(f"❌ No active subscription found for user {user_id}")
                return
            
            print(f"✅ Found subscription: {subscription.stripe_subscription_id}")
            
            # Get plan
            result = await session.execute(
                select(Plan).where(Plan.id == subscription.plan_id)
            )
            plan = result.scalar_one_or_none()
            
            if not plan:
                print(f"❌ Plan not found for subscription")
                return
            
            print(f"✅ Plan: {plan.display_name} ({plan.name})")
            print(f"   Credits per month: {plan.credits_per_month}")
            
            # Get wallet
            credits_service = CreditsService(session)
            wallet = await credits_service.get_wallet(user_id)
            old_balance = wallet.balance_credits
            
            # Grant credits (ensure user has at least plan amount)
            new_balance = max(wallet.balance_credits, plan.credits_per_month)
            
            if new_balance > old_balance:
                wallet.balance_credits = new_balance
                credit_amount = new_balance - old_balance
                
                # Record transaction
                from app.models.credits import CreditTransaction
                transaction = CreditTransaction(
                    user_id=user_id,
                    amount=credit_amount,
                    direction="credit",
                    reason="manual_grant",
                    metadata_json=f'{{"plan_name": "{plan.name}", "old_balance": {old_balance}, "new_balance": {new_balance}, "reason": "webhook_fix"}}'
                )
                session.add(transaction)
                session.add(wallet)
                await session.commit()
                
                print(f"✅ Granted {credit_amount} credits to user {user_id}")
                print(f"   Old balance: {old_balance}")
                print(f"   New balance: {new_balance}")
            else:
                print(f"ℹ️  User already has {old_balance} credits (plan provides {plan.credits_per_month})")
                if old_balance < plan.credits_per_month:
                    wallet.balance_credits = plan.credits_per_month
                    session.add(wallet)
                    await session.commit()
                    print(f"✅ Updated balance to {plan.credits_per_month}")
                else:
                    print(f"   No change needed")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    if len(sys.argv) > 1:
        email = sys.argv[1]
        print(f"Checking credits for email: {email}\n")
        
        # Simple async wrapper to find user by email then call grant_credits
        async def find_and_grant(email):
            async_session = sessionmaker(engine, class_=AsyncSessionType, expire_on_commit=False)
            async with async_session() as session:
                result = await session.execute(select(UserProfile).where(UserProfile.email == email))
                user = result.scalar_one_or_none()
                if user:
                    print(f"Found user ID: {user.id}")
                    await grant_credits_to_user(str(user.id))
                else:
                    print(f"User with email {email} not found")
        
        asyncio.run(find_and_grant(email))
    else:
        user_id = "0c8d5a8c-4d33-4d59-a664-7cba84bf45cd"
        print(f"Granting credits to user: {user_id}\n")
        asyncio.run(grant_credits_to_user(user_id))

