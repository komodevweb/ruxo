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
        "name": "free_trial",
        "display_name": "Free Trial",
        "amount_cents": 100,  # $1.00 one-time trial fee (not recurring)
        "interval": "one_time",  # One-time payment, not a subscription
        "credits_per_month": 50,  # 50 credits for trial
        "is_trial_plan": True,  # Special flag for trial plan
    },
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
                
                # Special handling for free_trial plan (no Stripe price needed)
                is_trial_plan = plan_config.get("is_trial_plan", False)
                
                if existing_plan:
                    if is_trial_plan:
                        print(f"Trial plan {plan_config['name']} already exists, skipping...")
                        continue
                    # Check if the Stripe price ID is valid
                    price_id_valid = False
                    try:
                        stripe.Price.retrieve(existing_plan.stripe_price_id)
                        price_id_valid = True
                        # print(f"Plan {plan_config['name']} already exists with valid price ID, updating DB records...")
                        # continue  # Removed continue to allow DB updates
                        price_id = existing_plan.stripe_price_id # Reuse existing price ID
                    except stripe.error.InvalidRequestError:
                        print(f"Plan {plan_config['name']} exists but price ID is invalid, updating...")
                        # Price ID is invalid, we'll create a new one and update the plan
                    except Exception as e:
                        print(f"Error checking price ID for {plan_config['name']}: {e}, will create new price...")
                
                # For trial plan, create a dummy price ID (not used in Stripe - it's just a DB record)
                # The $1 is charged as a one-time payment, not a subscription
                if is_trial_plan:
                    price_id = f"trial_plan_{plan_config['name']}_one_time"
                    product_id = None
                else:
                    # Create product in Stripe
                    product = stripe.Product.create(
                        name=plan_config["display_name"],
                        description=f"{plan_config['credits_per_month']} credits per month",
                    )
                    product_id = product.id
                    
                    # Create price in Stripe (use original price, discount applied via coupon at checkout)
                    price = stripe.Price.create(
                        product=product.id,
                        unit_amount=plan_config["amount_cents"],
                        currency="usd",
                        recurring={
                            "interval": plan_config["interval"],
                        },
                    )
                    price_id = price.id
                
                if existing_plan:
                    if is_trial_plan:
                        # For trial plan, just update credits if needed
                        existing_plan.credits_per_month = plan_config["credits_per_month"]
                        existing_plan.trial_credits = 50
                        session.add(existing_plan)
                        await session.commit()
                        print(f"[OK] Updated trial plan: {plan_config['display_name']} - ${plan_config['amount_cents']/100} one-time - {plan_config['credits_per_month']} credits (3-day trial)")
                    else:
                        # Update existing plan with new price ID and trial fields
                        existing_plan.stripe_price_id = price_id
                        existing_plan.trial_days = 3
                        existing_plan.trial_amount_cents = 100
                        existing_plan.trial_credits = 50  # 50 credits for trial
                        existing_plan.credits_per_month = plan_config["credits_per_month"]
                        existing_plan.amount_cents = plan_config["amount_cents"]
                        session.add(existing_plan)
                        await session.commit()
                        if is_trial_plan:
                            print(f"[OK] Updated trial plan: {plan_config['display_name']} - ${plan_config['amount_cents']/100} one-time - {plan_config['credits_per_month']} credits (3-day trial)")
                        else:
                            print(f"[OK] Updated plan: {plan_config['display_name']} - ${plan_config['amount_cents']/100}/{plan_config['interval']} - {plan_config['credits_per_month']} credits/month (Trial: 50 credits)")
                            print(f"  New Stripe Price ID: {price_id}")
                else:
                    # Create plan in database
                    plan = Plan(
                        id=uuid.uuid4(),
                        name=plan_config["name"],
                        display_name=plan_config["display_name"],
                        stripe_price_id=price_id,
                        credits_per_month=plan_config["credits_per_month"],
                        interval=plan_config["interval"],
                        amount_cents=plan_config["amount_cents"],
                        currency="usd",
                        trial_days=3,  # 3-day trial
                        trial_amount_cents=100,  # $1.00 trial
                        trial_credits=50,  # 50 credits during trial
                        is_active=True,
                        created_at=datetime.utcnow(),
                    )
                    
                    session.add(plan)
                    await session.commit()
                    
                    if is_trial_plan:
                        print(f"[OK] Created plan: {plan_config['display_name']} - ${plan_config['amount_cents']/100} one-time - {plan_config['credits_per_month']} credits (3-day trial)")
                    else:
                        print(f"[OK] Created plan: {plan_config['display_name']} - ${plan_config['amount_cents']/100}/{plan_config['interval']} - {plan_config['credits_per_month']} credits/month")
                        print(f"  Stripe Price ID: {price_id}")
                
                if plan_config["interval"] == "year":
                    print(f"  Note: 40% discount will be applied at checkout via coupon 'ruxo40'")
                
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

