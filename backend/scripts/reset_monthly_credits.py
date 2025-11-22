"""
Scheduled task to reset monthly credits for active subscriptions.

This should be run daily (via cron, Celery, or similar) to check for subscriptions
that need their credits reset at the start of a new billing period.

Usage:
    python scripts/reset_monthly_credits.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

# Add the backend directory to Python path so we can import app modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.session import engine
from app.models.billing import Subscription
from app.services.billing_service import BillingService
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession as AsyncSessionType

async def reset_monthly_credits():
    """Reset credits for subscriptions that have entered a new billing period."""
    async_session = sessionmaker(engine, class_=AsyncSessionType, expire_on_commit=False)
    async with async_session() as session:
        try:
            service = BillingService(session)
            
            # Find all active subscriptions
            result = await session.execute(
                select(Subscription).where(
                    and_(
                        Subscription.status == "active",
                        Subscription.last_credit_reset.isnot(None)
                    )
                )
            )
            subscriptions = result.scalars().all()
            
            reset_count = 0
            for subscription in subscriptions:
                # Use _check_and_reset_credits which handles both monthly and yearly plans
                # For monthly plans: resets when billing period changes
                # For yearly plans: resets every month
                try:
                    # Store old reset time to check if it changed
                    old_reset_time = subscription.last_credit_reset
                    await service._check_and_reset_credits(subscription)
                    # Refresh to get updated last_credit_reset
                    await session.refresh(subscription)
                    if subscription.last_credit_reset != old_reset_time:
                        reset_count += 1
                        print(f"Reset credits for subscription {subscription.id} (user {subscription.user_id})")
                except Exception as e:
                    print(f"Error checking/resetting credits for subscription {subscription.id}: {e}")
                    continue
            
            print(f"Reset credits for {reset_count} subscription(s)")
            
        except Exception as e:
            print(f"Error resetting credits: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    try:
        print("Checking for subscriptions that need credit resets...")
        asyncio.run(reset_monthly_credits())
        print("Done!")
    except ModuleNotFoundError as e:
        print(f"\nERROR: Missing module: {e}")
        print("\nMake sure you:")
        print("1. Are in the 'backend' directory")
        print("2. Have activated the virtual environment:")
        print("   Windows: venv\\Scripts\\activate")
        print("   Linux/Mac: source venv/bin/activate")
        print("3. Have installed dependencies: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

