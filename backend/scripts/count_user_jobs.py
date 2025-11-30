import asyncio
import sys
import uuid
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import AsyncSession as AsyncSessionType
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from app.db.session import engine
from app.models.render import RenderJob
from app.models.user import UserProfile

async def count_user_jobs(user_id_str: str):
    """Count jobs for a specific user."""
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
            
            # Get all jobs
            result = await session.execute(
                select(RenderJob)
                .where(RenderJob.user_id == user.id)
                .order_by(RenderJob.created_at.desc())
            )
            jobs = result.scalars().all()
            
            print(f"\n📊 Job History ({len(jobs)} total):")
            print(f"{'Created At':<25} | {'Status':<10} | {'Provider':<20} | {'Cost':<6} | {'Job ID'}")
            print("-" * 100)
            
            successful = 0
            failed = 0
            pending = 0
            
            for job in jobs:
                created_at = job.created_at.strftime("%Y-%m-%d %H:%M:%S") if job.created_at else "N/A"
                cost = job.actual_credit_cost or job.estimated_credit_cost or 0
                print(f"{created_at:<25} | {job.status:<10} | {job.provider:<20} | {cost:<6} | {job.id}")
                
                if job.status == "completed":
                    successful += 1
                elif job.status == "failed":
                    failed += 1
                else:
                    pending += 1
            
            print(f"\nSummary:")
            print(f"✅ Successful: {successful}")
            print(f"❌ Failed: {failed}")
            print(f"⏳ Pending/Running: {pending}")
            print(f"Total: {len(jobs)}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/count_user_jobs.py <user_id>")
        sys.exit(1)
    
    user_id = sys.argv[1]
    asyncio.run(count_user_jobs(user_id))

