import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.billing import Plan
from sqlalchemy.future import select

async def list_plans():
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        result = await session.execute(select(Plan))
        plans = result.scalars().all()
        
        print(f"Found {len(plans)} plans:")
        print("-" * 100)
        print(f"{'Name':<20} | {'ID':<36} | {'Stripe Price ID':<30}")
        print("-" * 100)
        for plan in plans:
            print(f"{plan.name:<20} | {str(plan.id):<36} | {plan.stripe_price_id:<30}")
        print("-" * 100)

if __name__ == "__main__":
    asyncio.run(list_plans())
