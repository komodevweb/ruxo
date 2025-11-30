
import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import select

# Add backend directory to path
sys.path.append(os.path.abspath("backend"))

# Import models
from app.models.billing import Plan

# Database URL from .env
DATABASE_URL = "postgresql+asyncpg://postgres:KSu1wZsobckLwdhu@db.cutgibszjdnxsrlclbos.supabase.co:5432/postgres"

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def inspect_plan():
    async with async_session_maker() as session:
        result = await session.exec(select(Plan).where(Plan.name == "starter_yearly"))
        plan = result.first()
        if plan:
            print(f"Plan: {plan.name}")
            print(f"Trial Days: {plan.trial_days}")
            print(f"Trial Credits: {plan.trial_credits}")
            print(f"Credits per Month: {plan.credits_per_month}")

if __name__ == "__main__":
    asyncio.run(inspect_plan())

