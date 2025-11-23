"""
Script to check all plans in the database and validate their Stripe price IDs.

This script will:
1. List all plans in the database with their price IDs
2. Validate each price ID exists in Stripe
3. Show which plans have invalid price IDs

Usage:
    python scripts/check_plans.py
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import stripe
from sqlalchemy.ext.asyncio import AsyncSession as AsyncSessionType
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import engine
from app.models.billing import Plan

stripe.api_key = settings.STRIPE_API_KEY

async def check_plans():
    """Check all plans and validate their Stripe price IDs."""
    async_session = sessionmaker(engine, class_=AsyncSessionType, expire_on_commit=False)
    async with async_session() as session:
        try:
            # Fetch all plans
            result = await session.execute(
                select(Plan).order_by(Plan.name)
            )
            plans = result.scalars().all()
            
            if not plans:
                print("No plans found in database.")
                return
            
            print(f"\n{'='*80}")
            print(f"Found {len(plans)} plan(s) in database")
            print(f"{'='*80}\n")
            
            invalid_plans = []
            
            for plan in plans:
                print(f"Plan: {plan.display_name} ({plan.name})")
                print(f"  ID: {plan.id}")
                print(f"  Stripe Price ID: {plan.stripe_price_id}")
                print(f"  Amount: ${plan.amount_cents/100}/{plan.interval}")
                print(f"  Credits: {plan.credits_per_month}/month")
                print(f"  Active: {plan.is_active}")
                
                # Validate price ID in Stripe
                try:
                    price = stripe.Price.retrieve(plan.stripe_price_id)
                    print(f"  ✓ Price ID is valid in Stripe")
                    print(f"    Product: {price.product}")
                    print(f"    Amount: ${price.unit_amount/100} {price.currency.upper()}")
                    print(f"    Interval: {price.recurring.interval if price.recurring else 'one-time'}")
                except stripe.error.InvalidRequestError as e:
                    if "No such price" in str(e):
                        print(f"  ✗ ERROR: Price ID does not exist in Stripe!")
                        invalid_plans.append(plan)
                    else:
                        print(f"  ✗ ERROR: {str(e)}")
                        invalid_plans.append(plan)
                except Exception as e:
                    print(f"  ✗ ERROR: {str(e)}")
                    invalid_plans.append(plan)
                
                print()
            
            if invalid_plans:
                print(f"\n{'='*80}")
                print(f"⚠️  WARNING: {len(invalid_plans)} plan(s) have invalid Stripe price IDs:")
                print(f"{'='*80}\n")
                for plan in invalid_plans:
                    print(f"  - {plan.display_name} ({plan.name})")
                    print(f"    Current Price ID: {plan.stripe_price_id}")
                    print(f"    Plan ID: {plan.id}")
                    print()
                print("\nTo fix this, you need to:")
                print("1. Create new prices in Stripe for these plans")
                print("2. Update the stripe_price_id in the database for each plan")
                print("3. Or run the seed_plans.py script to recreate all plans")
            else:
                print(f"\n{'='*80}")
                print("✓ All plans have valid Stripe price IDs!")
                print(f"{'='*80}\n")
                
        except Exception as e:
            print(f"Error checking plans: {e}")
            raise

if __name__ == "__main__":
    print("Checking plans in database and validating Stripe price IDs...")
    asyncio.run(check_plans())

