#!/usr/bin/env python3
"""
Script to find the user who triggered a specific job by job ID.
"""
import asyncio
import sys
import uuid
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Add backend to path
sys.path.insert(0, '/root/ruxo/backend')

# Load .env file
from dotenv import load_dotenv
backend_path = Path('/root/ruxo/backend')
env_path = backend_path / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    print(f"⚠️  Warning: .env file not found at {env_path}")

from app.core.config import settings
from app.models.render import RenderJob
from app.models.user import UserProfile

async def find_job_user(job_id_str: str):
    """Find the user who triggered a job by job ID."""
    try:
        # Parse the job ID
        try:
            job_id = uuid.UUID(job_id_str)
        except ValueError:
            print(f"❌ Invalid job ID format: {job_id_str}")
            print("   Job ID should be a valid UUID")
            return
        
        # Create database engine
        engine = create_async_engine(
            str(settings.DATABASE_URL),
            echo=False,
            pool_pre_ping=True
        )
        
        # Create async session
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session() as session:
            # Query for the job
            result = await session.execute(
                select(RenderJob).where(RenderJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job:
                print(f"❌ Job not found in render_jobs table: {job_id_str}")
                print("\n🔍 Searching for similar or recent jobs...")
                
                # Get some recent jobs to help debug
                recent_result = await session.execute(
                    select(RenderJob).order_by(RenderJob.created_at.desc()).limit(5)
                )
                recent_jobs = recent_result.scalars().all()
                
                if recent_jobs:
                    print(f"\n📋 Last 5 jobs in database:")
                    for j in recent_jobs:
                        print(f"  - {j.id} | {j.job_type} | {j.status} | {j.created_at}")
                else:
                    print("  No jobs found in database")
                
                # Also search in other potential ID fields (like task_id, wavespeed_id, etc.)
                from sqlalchemy import text
                print(f"\n🔍 Searching for '{job_id_str}' in job metadata/settings...")
                
                # Search in JSON fields
                json_search = await session.execute(
                    text("""
                        SELECT id, user_id, job_type, provider, status, created_at 
                        FROM render_jobs 
                        WHERE settings::text LIKE :search_term
                        LIMIT 5
                    """),
                    {"search_term": f"%{job_id_str}%"}
                )
                json_results = json_search.fetchall()
                
                if json_results:
                    print(f"\n✅ Found jobs with matching metadata:")
                    for row in json_results:
                        print(f"  Job ID: {row[0]}")
                        print(f"  User ID: {row[1]}")
                        print(f"  Type: {row[2]} | Provider: {row[3]} | Status: {row[4]}")
                        print(f"  Created: {row[5]}")
                        print()
                        
                        # Get the user
                        user_result = await session.execute(
                            select(UserProfile).where(UserProfile.id == row[1])
                        )
                        user = user_result.scalar_one_or_none()
                        
                        if user:
                            display_name = user.display_name or "N/A"
                            print(f"  👤 User: {user.email} (Display Name: {display_name})")
                            print(f"{'='*60}\n")
                else:
                    print("  No matches found in job metadata")
                
                return
            
            # Get the user
            user_result = await session.execute(
                select(UserProfile).where(UserProfile.id == job.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                print(f"❌ User not found for job {job_id_str}")
                print(f"   User ID: {job.user_id}")
                return
            
            # Display results
            print(f"\n✅ Job Found!")
            print(f"\n{'='*60}")
            print(f"Job ID:       {job.id}")
            print(f"Job Type:     {job.job_type}")
            print(f"Provider:     {job.provider}")
            print(f"Status:       {job.status}")
            print(f"Created:      {job.created_at}")
            print(f"Updated:      {job.updated_at}")
            print(f"\n{'='*60}")
            print(f"User ID:      {user.id}")
            print(f"Email:        {user.email}")
            display_name = user.display_name or "N/A"
            print(f"Display Name: {display_name}")
            print(f"Created:      {user.created_at}")
            print(f"{'='*60}\n")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find_job_user.py <job_id>")
        print("\nExample:")
        print("  python find_job_user.py b50bd6b0be9f4dbe8401ee831fab09e3")
        print("  python find_job_user.py e35c4586-e2f3-4c18-bbed-922020646955")
        print("\nNote: Can search by database job ID (UUID) or WaveSpeed task ID")
        sys.exit(1)
    
    job_id = sys.argv[1]
    asyncio.run(find_job_user(job_id))

