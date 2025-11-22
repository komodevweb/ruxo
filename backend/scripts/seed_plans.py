"""
Script to seed Stripe products/prices and database plans.

Run this script to:
1. Create products and prices in Stripe
2. Create corresponding Plan records in the database

Usage:
    python scripts/seed_plans.py
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import stripe
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession as AsyncSessionType
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import engine
from app.models.billing import Plan

stripe.api_key = settings.STRIPE_API_KEY

# Plan configurations
PLANS = [
    {
        "name": "starter_monthly",
        "display_name": "Starter Monthly",
        "amount_cents": 2000,  # $20.00
        "interval": "month",
        "credits_per_month": 200,
    },
    {
        "name": "starter_yearly",
        "display_name": "Starter Yearly",
        "amount_cents": 20000,  # $200.00 (approx $16.67/month)
        "interval": "year",
        "credits_per_month": 200,
    },
    {
        "name": "pro_monthly",
        "display_name": "Pro Monthly",
        "amount_cents": 3900,  # $39.00
        "interval": "month",
        "credits_per_month": 400,
    },
    {
        "name": "pro_yearly",
        "display_name": "Pro Yearly",
        "amount_cents": 39000,  # $390.00 (approx $32.50/month)
        "interval": "year",
        "credits_per_month": 400,
    },
    {
        "name": "creator_monthly",
        "display_name": "Creator Monthly",
        "amount_cents": 9900,  # $99.00
        "interval": "month",
        "credits_per_month": 1000,
    },
    {
        "name": "creator_yearly",
        "display_name": "Creator Yearly",
        "amount_cents": 99000,  # $990.00 (approx $82.50/month)
        "interval": "year",
        "credits_per_month": 1000,
    },
    {
        "name": "ultimate_monthly",
        "display_name": "Ultimate Monthly",
        "amount_cents": 20000,  # $200.00
        "interval": "month",
        "credits_per_month": 2000,
    },
    {
        "name": "ultimate_yearly",
        "display_name": "Ultimate Yearly",
        "amount_cents": 200000,  # $2000.00 (approx $166.67/month)
        "interval": "year",
        "credits_per_month": 2000,
    },
]

async def seed_plans():
    """Create Stripe products/prices and database plans."""
    async_session = sessionmaker(engine, class_=AsyncSessionType, expire_on_commit=False)
    async with async_session() as session:
        try:
            for plan_config in PLANS:
                # Check if plan already exists in database
                result = await session.execute(
                    select(Plan).where(Plan.name == plan_config["name"])
                )
                existing_plan = result.scalar_one_or_none()
                
                if existing_plan:
                    print(f"Plan {plan_config['name']} already exists, skipping...")
                    continue
                
                # Create product in Stripe
                product = stripe.Product.create(
                    name=plan_config["display_name"],
                    description=f"{plan_config['credits_per_month']} credits per month",
                )
                
                # Create price in Stripe (use original price, discount applied via coupon at checkout)
                price = stripe.Price.create(
                    product=product.id,
                    unit_amount=plan_config["amount_cents"],
                    currency="usd",
                    recurring={
                        "interval": plan_config["interval"],
                    },
                )
                
                # Create plan in database
                plan = Plan(
                    id=uuid.uuid4(),
                    name=plan_config["name"],
                    display_name=plan_config["display_name"],
                    stripe_price_id=price.id,
                    credits_per_month=plan_config["credits_per_month"],
                    interval=plan_config["interval"],
                    amount_cents=plan_config["amount_cents"],
                    currency="usd",
                    is_active=True,
                    created_at=datetime.utcnow(),
                )
                
                session.add(plan)
                await session.commit()
                
                print(f"[OK] Created plan: {plan_config['display_name']} - ${plan_config['amount_cents']/100}/{plan_config['interval']} - {plan_config['credits_per_month']} credits/month")
                if plan_config["interval"] == "year":
                    print(f"  Note: 40% discount will be applied at checkout via coupon 'ruxo40'")
                print(f"  Stripe Price ID: {price.id}")
                
        except Exception as e:
            print(f"Error seeding plans: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    print("Seeding plans in Stripe and database...")
    try:
        asyncio.run(seed_plans())
        print("\nDone! Plans have been created.")
        
        # Invalidate cache so plans show up immediately
        from app.routers.billing import invalidate_plans_cache
        invalidate_plans_cache()
        print("Cache invalidated - plans will be visible immediately.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

