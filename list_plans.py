
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

async def list_plans():
    async with async_session_maker() as session:
        result = await session.exec(select(Plan))
        plans = result.all()
        print(f"Found {len(plans)} plans:")
        for plan in plans:
            print(f"ID: {plan.id}, Name: {plan.name}, Display: {plan.display_name}")

if __name__ == "__main__":
    asyncio.run(list_plans())
