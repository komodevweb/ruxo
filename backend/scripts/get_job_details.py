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

async def get_job_details(job_id_str: str):
    """Get details for a specific render job."""
    async_session = sessionmaker(engine, class_=AsyncSessionType, expire_on_commit=False)
    async with async_session() as session:
        try:
            # Parse job ID
            try:
                job_id = uuid.UUID(job_id_str)
            except ValueError:
                print(f"❌ Invalid job ID format: {job_id_str}")
                return
            
            # Find job
            result = await session.execute(
                select(RenderJob).where(RenderJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job:
                print(f"❌ Job not found: {job_id}")
                return
            
            print(f"✓ Found job: {job.id}")
            print(f"  Status: {job.status}")
            print(f"  Provider: {job.provider}")
            print(f"  Created At: {job.created_at}")
            print(f"  Input Prompt: {job.input_prompt}")
            
            if job.output_url:
                print(f"\n🔗 Output URL: {job.output_url}")
            else:
                print(f"\n❌ No output URL found (Status: {job.status})")
                if job.error_message:
                    print(f"  Error: {job.error_message}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/get_job_details.py <job_id>")
        sys.exit(1)
    
    job_id = sys.argv[1]
    asyncio.run(get_job_details(job_id))

