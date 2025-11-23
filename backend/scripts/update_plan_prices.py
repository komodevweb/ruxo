"""
Script to update existing plans in the database with new Stripe price IDs.

This script will:
1. For each existing plan, create a new price in Stripe
2. Update the plan's stripe_price_id in the database

Usage:
    python scripts/update_plan_prices.py
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

async def update_plan_prices():
    """Update existing plans with new Stripe price IDs."""
    async_session = sessionmaker(engine, class_=AsyncSessionType, expire_on_commit=False)
    async with async_session() as session:
        try:
            # Fetch all active plans
            result = await session.execute(
                select(Plan).where(Plan.is_active == True).order_by(Plan.name)
            )
            plans = result.scalars().all()
            
            if not plans:
                print("No active plans found in database.")
                return
            
            print(f"\n{'='*80}")
            print(f"Found {len(plans)} active plan(s) to update")
            print(f"{'='*80}\n")
            
            updated_count = 0
            
            for plan in plans:
                print(f"Updating: {plan.display_name} ({plan.name})")
                print(f"  Current Price ID: {plan.stripe_price_id}")
                
                try:
                    # Check if current price exists
                    try:
                        existing_price = stripe.Price.retrieve(plan.stripe_price_id)
                        print(f"  ✓ Current price ID is valid, skipping...")
                        print()
                        continue
                    except stripe.error.InvalidRequestError:
                        # Price doesn't exist, create new one
                        pass
                    
                    # Create product in Stripe (or find existing one)
                    product_name = plan.display_name
                    products = stripe.Product.list(limit=100)
                    product = None
                    for p in products.data:
                        if p.name == product_name:
                            product = p
                            break
                    
                    if not product:
                        product = stripe.Product.create(
                            name=product_name,
                            description=f"{plan.credits_per_month} credits per month",
                        )
                        print(f"  Created new product: {product.id}")
                    else:
                        print(f"  Using existing product: {product.id}")
                    
                    # Create new price in Stripe
                    price = stripe.Price.create(
                        product=product.id,
                        unit_amount=plan.amount_cents,
                        currency=plan.currency,
                        recurring={
                            "interval": plan.interval,
                        },
                    )
                    
                    # Update plan with new price ID
                    old_price_id = plan.stripe_price_id
                    plan.stripe_price_id = price.id
                    session.add(plan)
                    await session.commit()
                    
                    print(f"  ✓ Updated price ID: {old_price_id} -> {price.id}")
                    print(f"  New Price ID: {price.id}")
                    updated_count += 1
                    
                except Exception as e:
                    print(f"  ✗ ERROR: {str(e)}")
                    await session.rollback()
                
                print()
            
            print(f"\n{'='*80}")
            if updated_count > 0:
                print(f"✓ Successfully updated {updated_count} plan(s)")
            else:
                print("No plans needed updating (all price IDs are valid)")
            print(f"{'='*80}\n")
                
        except Exception as e:
            print(f"Error updating plans: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    print("Updating plan price IDs in Stripe and database...")
    asyncio.run(update_plan_prices())

