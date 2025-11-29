"""
Script to remove/cancel a user's subscription plan.

Usage:
    python scripts/remove_user_plan.py <user_id> [--remove-credits]
    
Examples:
    python scripts/remove_user_plan.py bb695da1-4f49-4995-8592-d4878f512518
    python scripts/remove_user_plan.py bb695da1-4f49-4995-8592-d4878f512518 --remove-credits
"""

import asyncio
import sys
import uuid
import argparse
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import stripe
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession as AsyncSessionType
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import engine
from app.models.billing import Subscription
from app.models.user import UserProfile
from app.services.credits_service import CreditsService

stripe.api_key = settings.STRIPE_API_KEY

async def remove_user_plan(user_id_str: str, remove_credits: bool = False):
    """Remove/cancel a user's subscription plan."""
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
            
            # Find all subscriptions for this user (active, trialing, past_due, etc.)
            result = await session.execute(
                select(Subscription).where(Subscription.user_id == user.id)
            )
            subscriptions = result.scalars().all()
            
            if not subscriptions:
                print(f"⚠️  No subscriptions found for user {user_id}")
                return
            
            print(f"\n📋 Found {len(subscriptions)} subscription(s):")
            for sub in subscriptions:
                print(f"  - {sub.stripe_subscription_id} ({sub.status}) - {sub.plan_name}")
            
            credits_service = CreditsService(session)
            
            # Cancel all subscriptions
            for subscription in subscriptions:
                print(f"\n🔄 Processing subscription: {subscription.stripe_subscription_id}")
                print(f"   Status: {subscription.status}")
                print(f"   Plan: {subscription.plan_name}")
                
                # Only try to cancel in Stripe if it's not an admin subscription
                if not subscription.stripe_subscription_id.startswith("admin_"):
                    try:
                        # Cancel in Stripe immediately
                        stripe.Subscription.delete(subscription.stripe_subscription_id)
                        print(f"   ✓ Canceled subscription in Stripe")
                    except stripe.error.InvalidRequestError as e:
                        if "No such subscription" in str(e) or "already been deleted" in str(e):
                            print(f"   ⚠️  Subscription already deleted in Stripe")
                        else:
                            print(f"   ⚠️  Stripe error: {e}")
                    except Exception as e:
                        print(f"   ⚠️  Error canceling in Stripe: {e}")
                else:
                    print(f"   ⚠️  Admin subscription - skipping Stripe cancellation")
                
                # Update database
                subscription.status = "canceled"
                subscription.updated_at = datetime.utcnow()
                session.add(subscription)
                print(f"   ✓ Updated subscription status in database")
            
            await session.commit()
            print(f"\n✓ Updated all subscriptions in database")
            
            # Remove credits if requested
            if remove_credits:
                print(f"\n💰 Removing user credits...")
                wallet = await credits_service.get_wallet(user.id)
                if wallet.balance_credits > 0:
                    old_balance = wallet.balance_credits
                    await credits_service.spend_credits(
                        user_id=user.id,
                        amount=wallet.balance_credits,
                        reason="subscription_removed",
                        metadata={
                            "user_id": str(user.id),
                            "old_balance": old_balance,
                            "removed_by": "admin_script"
                        }
                    )
                    print(f"✓ Removed {old_balance} credits")
                else:
                    print(f"✓ User already has 0 credits")
            
            # Show final status
            result = await session.execute(
                select(Subscription).where(Subscription.user_id == user.id)
            )
            final_subs = result.scalars().all()
            
            wallet = await credits_service.get_wallet(user.id)
            
            print(f"\n{'='*80}")
            print(f"✅ Successfully removed plan from user!")
            print(f"{'='*80}")
            print(f"User: {user.email}")
            print(f"Subscriptions: {len(final_subs)} (all canceled)")
            print(f"Credits: {wallet.balance_credits}")
            print(f"{'='*80}\n")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remove/cancel a user's subscription plan")
    parser.add_argument("user_id", help="User ID (UUID)")
    parser.add_argument("--remove-credits", action="store_true", help="Also remove all user credits")
    
    args = parser.parse_args()
    
    print(f"Removing plan from user {args.user_id}...")
    if args.remove_credits:
        print("⚠️  Credits will also be removed\n")
    else:
        print("ℹ️  Credits will be preserved (use --remove-credits to remove them)\n")
    
    asyncio.run(remove_user_plan(args.user_id, args.remove_credits))

