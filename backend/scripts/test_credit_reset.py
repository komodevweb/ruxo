"""
Test script to verify monthly credit reset for yearly subscriptions.

This script can:
1. Simulate time passing by modifying last_credit_reset dates
2. Test the credit reset logic
3. Verify yearly plans get reset monthly
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Change to backend directory so .env file is found
import os
os.chdir(backend_dir)

from app.db.session import engine
from app.models.billing import Subscription, Plan
from app.services.billing_service import BillingService
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession as AsyncSessionType


async def test_credit_reset():
    """Test the credit reset logic."""
    async_session = sessionmaker(engine, class_=AsyncSessionType, expire_on_commit=False)
    async with async_session() as session:
        try:
            service = BillingService(session)
            
            # Find all active subscriptions
            result = await session.execute(
                select(Subscription).where(Subscription.status == "active")
            )
            subscriptions = result.scalars().all()
            
            if not subscriptions:
                print("No active subscriptions found. Create a subscription first.")
                return
            
            print(f"\nFound {len(subscriptions)} active subscription(s):\n")
            
            for sub in subscriptions:
                # Get plan info
                plan_result = await session.execute(
                    select(Plan).where(Plan.id == sub.plan_id)
                )
                plan = plan_result.scalar_one_or_none()
                
                plan_name = plan.name if plan else "Unknown"
                plan_interval = plan.interval if plan else "Unknown"
                
                print(f"Subscription {sub.id}:")
                print(f"  Plan: {plan_name} ({plan_interval})")
                print(f"  User: {sub.user_id}")
                print(f"  Last Reset: {sub.last_credit_reset}")
                print(f"  Current Period Start: {sub.current_period_start}")
                
                # Check if reset would happen
                if sub.last_credit_reset:
                    if plan and plan.interval == "year":
                        # For yearly plans, check if a month has passed
                        now = datetime.utcnow()
                        # Normalize timezones for comparison
                        last_reset = sub.last_credit_reset
                        if now.tzinfo is None and last_reset.tzinfo is not None:
                            from datetime import timezone
                            now = now.replace(tzinfo=timezone.utc)
                        elif now.tzinfo is not None and last_reset.tzinfo is None:
                            from datetime import timezone
                            last_reset = last_reset.replace(tzinfo=timezone.utc)
                        
                        months_since_reset = (now.year - last_reset.year) * 12 + (now.month - last_reset.month)
                        print(f"  Months since last reset: {months_since_reset}")
                        if months_since_reset >= 1:
                            print(f"  ✅ Would reset (monthly reset for yearly plan)")
                        else:
                            print(f"  ⏳ Not yet time to reset (needs 1+ month)")
                    else:
                        # For monthly plans, check billing period
                        # Normalize timezones for comparison
                        period_start = sub.current_period_start
                        last_reset = sub.last_credit_reset
                        if period_start.tzinfo is None and last_reset.tzinfo is not None:
                            from datetime import timezone
                            period_start = period_start.replace(tzinfo=timezone.utc)
                        elif period_start.tzinfo is not None and last_reset.tzinfo is None:
                            from datetime import timezone
                            last_reset = last_reset.replace(tzinfo=timezone.utc)
                        
                        if period_start > last_reset:
                            print(f"  ✅ Would reset (new billing period)")
                        else:
                            print(f"  ⏳ Not yet time to reset (billing period hasn't changed)")
                else:
                    print(f"  ⚠️  No last_credit_reset set (will be set on first check)")
                
                print()
            
            # Ask user if they want to simulate time passing
            print("\n" + "="*60)
            print("SIMULATION OPTIONS:")
            print("1. Run actual credit reset (checks and resets if needed)")
            print("2. Simulate 30 days passing (modify last_credit_reset for yearly plans)")
            print("3. Both (simulate then reset)")
            print("4. Exit")
            print("\n⚠️  NOTE: After simulating (option 2), you MUST run option 1 to actually reset credits!")
            
            choice = input("\nEnter choice (1-4): ").strip()
            
            if choice == "1":
                await run_actual_reset(service, session, subscriptions)
            elif choice == "2":
                await simulate_time_passing(session, subscriptions)
            elif choice == "3":
                await simulate_time_passing(session, subscriptions)
                await run_actual_reset(service, session, subscriptions)
            else:
                print("Exiting...")
                return
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()


async def simulate_time_passing(session: AsyncSession, subscriptions: list):
    """Simulate 30 days passing by modifying last_credit_reset dates."""
    print("\n" + "="*60)
    print("SIMULATING 30 DAYS PASSING...")
    print("="*60)
    
    for sub in subscriptions:
        # Get plan to check if it's yearly
        plan_result = await session.execute(
            select(Plan).where(Plan.id == sub.plan_id)
        )
        plan = plan_result.scalar_one_or_none()
        
        if plan and plan.interval == "year" and sub.last_credit_reset:
            # Set last_credit_reset to 31 days ago (ensures monthly reset will trigger)
            new_reset_date = datetime.utcnow() - timedelta(days=31)
            sub.last_credit_reset = new_reset_date
            session.add(sub)
            print(f"✅ Updated subscription {sub.id} ({plan.name}):")
            print(f"   Last reset set to: {new_reset_date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   (31 days ago - will trigger monthly reset)")
        elif plan and plan.interval == "month":
            print(f"⏭️  Skipping subscription {sub.id} ({plan.name}): Monthly plan (not simulating)")
        else:
            print(f"⚠️  Subscription {sub.id}: No plan or last_credit_reset found")
    
    await session.commit()
    print("\n✅ Simulation complete! last_credit_reset dates updated.")
    print("   Now run option 1 to test the actual reset.")


async def run_actual_reset(service: BillingService, session: AsyncSession, subscriptions: list):
    """Run the actual credit reset logic."""
    print("\n" + "="*60)
    print("RUNNING ACTUAL CREDIT RESET...")
    print("="*60)
    
    reset_count = 0
    for subscription in subscriptions:
        try:
            # Get plan info
            plan_result = await session.execute(
                select(Plan).where(Plan.id == subscription.plan_id)
            )
            plan = plan_result.scalar_one_or_none()
            plan_name = plan.name if plan else "Unknown"
            plan_interval = plan.interval if plan else "Unknown"
            
            # Store old reset time and balance
            old_reset_time = subscription.last_credit_reset
            old_balance = None
            if subscription.user_id:
                from app.services.credits_service import CreditsService
                credits_service = CreditsService(session)
                wallet = await credits_service.get_wallet(subscription.user_id)
                old_balance = wallet.balance_credits
            
            print(f"\nChecking subscription {subscription.id} ({plan_name}, {plan_interval})...")
            
            # Run the check
            await service._check_and_reset_credits(subscription)
            
            # Refresh to get updated values
            await session.refresh(subscription)
            
            # Check if reset happened
            if subscription.last_credit_reset != old_reset_time:
                reset_count += 1
                new_balance = None
                if subscription.user_id:
                    wallet = await credits_service.get_wallet(subscription.user_id)
                    new_balance = wallet.balance_credits
                
                print(f"  ✅ CREDITS RESET!")
                print(f"     Last reset: {old_reset_time} → {subscription.last_credit_reset}")
                if old_balance is not None and new_balance is not None:
                    print(f"     Balance: {old_balance} → {new_balance} credits")
                    if plan:
                        print(f"     Expected: {plan.credits_per_month} credits")
                        if new_balance == plan.credits_per_month:
                            print(f"     ✅ Balance matches plan amount!")
                        else:
                            print(f"     ⚠️  Balance doesn't match plan amount!")
            else:
                print(f"  ⏳ No reset needed (not yet time)")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n" + "="*60)
    print(f"SUMMARY: Reset credits for {reset_count} subscription(s)")
    print("="*60)


if __name__ == "__main__":
    print("="*60)
    print("CREDIT RESET TEST SCRIPT")
    print("="*60)
    print("\nThis script helps you test the monthly credit reset logic")
    print("for yearly subscriptions.\n")
    
    asyncio.run(test_credit_reset())
    print("\nDone!")

