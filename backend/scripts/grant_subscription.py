"""
Script to grant a subscription plan to a user (admin upgrade).

Usage:
    python scripts/grant_subscription.py <user_id> <plan_name> [duration_days]
    
Examples:
    python scripts/grant_subscription.py c31811c5-846c-4526-b726-d1dd88c13224 pro_monthly 30
    python scripts/grant_subscription.py c31811c5-846c-4526-b726-d1dd88c13224 ultimate_yearly 365
"""

import asyncio
import sys
import uuid
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import stripe
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession as AsyncSessionType
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import engine
from app.models.billing import Subscription, Plan
from app.models.user import UserProfile
from app.services.billing_service import BillingService
from app.services.credits_service import CreditsService

stripe.api_key = settings.STRIPE_API_KEY

async def grant_subscription(user_id_str: str, plan_name: str, duration_days: int = None):
    """Grant a subscription plan to a user."""
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
            
            # Find the requested plan
            result = await session.execute(
                select(Plan).where(Plan.name == plan_name, Plan.is_active == True)
            )
            plan = result.scalar_one_or_none()
            
            if not plan:
                print(f"❌ Plan '{plan_name}' not found in database")
                print("\nAvailable plans:")
                result = await session.execute(select(Plan).where(Plan.is_active == True))
                plans = result.scalars().all()
                for p in plans:
                    print(f"  - {p.name} ({p.display_name})")
                return
            
            print(f"✓ Found plan: {plan.display_name} (${plan.amount_cents/100}/{plan.interval})")
            print(f"  Credits: {plan.credits_per_month}/month")
            print(f"  Stripe Price ID: {plan.stripe_price_id}")
            
            # Check for existing subscription
            result = await session.execute(
                select(Subscription).where(
                    Subscription.user_id == user.id,
                    Subscription.status.in_(["active", "trialing"])
                )
            )
            existing_sub = result.scalar_one_or_none()
            
            billing_service = BillingService(session)
            credits_service = CreditsService(session)
            
            # Get or create Stripe customer
            customer_id = await billing_service._get_or_create_customer(user)
            print(f"✓ Stripe Customer ID: {customer_id}")
            
            # Cancel existing subscription if any
            if existing_sub:
                print(f"\n⚠️  Found existing active subscription: {existing_sub.stripe_subscription_id}")
                print(f"   Status: {existing_sub.status}")
                print(f"   Plan: {existing_sub.plan_name}")
                
                # Only try to cancel in Stripe if it's not an admin subscription
                if not existing_sub.stripe_subscription_id.startswith("admin_"):
                    try:
                        # Cancel in Stripe
                        stripe.Subscription.delete(existing_sub.stripe_subscription_id)
                        print(f"✓ Canceled subscription in Stripe")
                    except stripe.error.InvalidRequestError as e:
                        if "No such subscription" in str(e):
                            print(f"⚠️  Subscription already deleted in Stripe")
                        else:
                            raise
                else:
                    print(f"⚠️  Existing subscription is an admin grant, canceling in database only")
                
                # Update database
                existing_sub.status = "canceled"
                existing_sub.updated_at = datetime.utcnow()
                session.add(existing_sub)
                await session.commit()
                print(f"✓ Updated subscription status in database")
            
            # For admin upgrades, create subscription directly in database without Stripe payment
            # This bypasses the payment method requirement
            print(f"\n📦 Creating subscription (admin grant - bypassing Stripe payment)...")
            
            # Calculate subscription period
            period_start = datetime.utcnow()
            if duration_days:
                period_end = period_start + timedelta(days=duration_days)
            elif plan.interval == "year":
                period_end = period_start + timedelta(days=365)
            else:
                period_end = period_start + timedelta(days=30)
            
            # Create a mock Stripe subscription ID for admin upgrades
            # Format: admin_<timestamp>_<user_id_short>
            admin_subscription_id = f"admin_{int(datetime.utcnow().timestamp())}_{str(user.id)[:8]}"
            
            new_subscription = Subscription(
                id=uuid.uuid4(),
                user_id=user.id,
                plan_id=plan.id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=admin_subscription_id,
                plan_name=plan.name,
                status="active",
                current_period_start=period_start,
                current_period_end=period_end,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            session.add(new_subscription)
            await session.commit()
            print(f"✓ Created subscription record in database")
            print(f"  Subscription ID: {admin_subscription_id}")
            print(f"  Status: active")
            print(f"  Period: {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}")
            
            # Add credits directly
            print(f"\n💰 Adding subscription credits...")
            wallet = await credits_service.get_wallet(user.id)
            current_credits = wallet.balance_credits
            
            # For upgrades, we typically set credits to the plan amount
            # If user already has credits, we add the difference
            credits_to_add = plan.credits_per_month - current_credits
            
            if credits_to_add > 0:
                await credits_service.add_credits(
                    user_id=user.id,
                    amount=credits_to_add,
                    reason="admin_grant",
                    metadata={
                        "plan_id": str(plan.id),
                        "plan_name": plan.name,
                        "subscription_id": str(new_subscription.id),
                        "old_balance": current_credits,
                        "new_balance": plan.credits_per_month
                    }
                )
                print(f"✓ Added {credits_to_add} credits (total: {plan.credits_per_month})")
            else:
                print(f"✓ User already has {current_credits} credits (plan provides {plan.credits_per_month})")
            
            # Refresh wallet to get final balance
            wallet = await credits_service.get_wallet(user.id)
            
            print(f"\n{'='*80}")
            print(f"✅ Successfully granted {plan.display_name} to user!")
            print(f"{'='*80}")
            print(f"User: {user.email}")
            print(f"Plan: {plan.display_name}")
            print(f"Credits: {wallet.balance_credits}")
            print(f"Subscription ID: {admin_subscription_id}")
            print(f"Status: active")
            print(f"Period: {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}")
            print(f"Duration: {(period_end - period_start).days} days")
            print(f"{'='*80}\n")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/grant_subscription.py <user_id> <plan_name> [duration_days]")
        print("\nExamples:")
        print("  python scripts/grant_subscription.py c31811c5-846c-4526-b726-d1dd88c13224 pro_monthly 30")
        print("  python scripts/grant_subscription.py c31811c5-846c-4526-b726-d1dd88c13224 ultimate_yearly 365")
        sys.exit(1)
    
    user_id = sys.argv[1]
    plan_name = sys.argv[2]
    duration_days = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    print(f"Granting {plan_name} subscription to user {user_id}...")
    if duration_days:
        print(f"Duration: {duration_days} days\n")
    else:
        print(f"Duration: Default for plan\n")
    
    asyncio.run(grant_subscription(user_id, plan_name, duration_days))
