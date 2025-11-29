"""
Scheduler service for periodic tasks using APScheduler.

This service handles scheduled tasks like monthly credit resets for yearly subscriptions.
The scheduler runs in-process with the FastAPI application.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_

from app.db.session import engine
from app.models.billing import Subscription
from app.models.render import RenderJob
from app.services.billing_service import BillingService
from app.services.wavespeed_service import WaveSpeedService
from app.services.credits_service import CreditsService
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession as AsyncSessionType
from datetime import datetime

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: AsyncIOScheduler = None


async def reset_monthly_credits_task():
    """Task to reset monthly credits for active subscriptions."""
    logger.info("="*60)
    logger.info("Starting scheduled credit reset task...")
    logger.info("="*60)
    
    async_session = sessionmaker(engine, class_=AsyncSessionType, expire_on_commit=False)
    async with async_session() as session:
        try:
            service = BillingService(session)
            
            # Find all active subscriptions
            result = await session.execute(
                select(Subscription).where(
                    and_(
                        Subscription.status == "active",
                        Subscription.last_credit_reset.isnot(None)
                    )
                )
            )
            subscriptions = result.scalars().all()
            
            logger.info(f"Found {len(subscriptions)} active subscription(s) to check")
            
            reset_count = 0
            yearly_reset_count = 0
            monthly_reset_count = 0
            
            for subscription in subscriptions:
                # Get plan info for logging
                from app.models.billing import Plan
                plan_result = await session.execute(
                    select(Plan).where(Plan.id == subscription.plan_id)
                )
                plan = plan_result.scalar_one_or_none()
                plan_name = plan.name if plan else "Unknown"
                plan_interval = plan.interval if plan else "Unknown"
                
                # Use _check_and_reset_credits which handles both monthly and yearly plans
                # For monthly plans: resets when billing period changes
                # For yearly plans: resets every month
                try:
                    # Store old reset time and balance to check if it changed
                    old_reset_time = subscription.last_credit_reset
                    old_balance = None
                    if subscription.user_id:
                        from app.services.credits_service import CreditsService
                        credits_service = CreditsService(session)
                        wallet = await credits_service.get_wallet(subscription.user_id)
                        old_balance = wallet.balance_credits
                    
                    logger.info(f"Checking subscription {subscription.id} ({plan_name}, {plan_interval})...")
                    logger.info(f"  Last reset: {old_reset_time}")
                    logger.info(f"  Current balance: {old_balance} credits")
                    
                    await service._check_and_reset_credits(subscription)
                    
                    # Refresh to get updated last_credit_reset
                    await session.refresh(subscription)
                    
                    if subscription.last_credit_reset != old_reset_time:
                        reset_count += 1
                        new_balance = None
                        if subscription.user_id:
                            wallet = await credits_service.get_wallet(subscription.user_id)
                            new_balance = wallet.balance_credits
                        
                        if plan and plan.interval == "year":
                            yearly_reset_count += 1
                            logger.info(f"  ✅ YEARLY PLAN: Credits reset monthly!")
                        else:
                            monthly_reset_count += 1
                            logger.info(f"  ✅ MONTHLY PLAN: Credits reset (billing period changed)")
                        
                        logger.info(f"  Last reset: {old_reset_time} → {subscription.last_credit_reset}")
                        logger.info(f"  Balance: {old_balance} → {new_balance} credits")
                        if plan:
                            logger.info(f"  Plan credits/month: {plan.credits_per_month}")
                            if new_balance == plan.credits_per_month:
                                logger.info(f"  ✅ Balance correctly set to plan amount!")
                    else:
                        logger.info(f"  ⏳ No reset needed (not yet time for this subscription)")
                        
                except Exception as e:
                    logger.error(f"Error checking/resetting credits for subscription {subscription.id}: {e}", exc_info=True)
                    continue
            
            logger.info("="*60)
            logger.info(f"Credit reset task completed:")
            logger.info(f"  Total subscriptions checked: {len(subscriptions)}")
            logger.info(f"  Total resets: {reset_count}")
            logger.info(f"  Yearly plan resets: {yearly_reset_count}")
            logger.info(f"  Monthly plan resets: {monthly_reset_count}")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Error in credit reset task: {e}", exc_info=True)
            await session.rollback()


async def check_active_jobs_task():
    """
    Task to check status of active jobs (pending/running) and update them.
    Also checks completed jobs that are missing output_url.
    Runs frequently to ensure data is up-to-date even if users aren't polling.
    """
    async_session = sessionmaker(engine, class_=AsyncSessionType, expire_on_commit=False)
    async with async_session() as session:
        try:
            # Find active jobs or completed jobs without output URL
            # Limit to 50 to prevent overwhelming the API in a single batch
            result = await session.execute(
                select(RenderJob)
                .where(
                    or_(
                        RenderJob.status.in_(["pending", "running"]),
                        and_(RenderJob.status == "completed", RenderJob.output_url.is_(None))
                    )
                )
                .order_by(RenderJob.updated_at.asc())  # Check oldest updated first
                .limit(50)
            )
            jobs = result.scalars().all()
            
            if not jobs:
                return

            wavespeed_service = WaveSpeedService()
            if not wavespeed_service.api_key:
                logger.warning("WaveSpeed API key not configured, skipping background job check")
                return

            updated_count = 0
            
            for job in jobs:
                wavespeed_task_id = job.settings.get('wavespeed_task_id')
                if not wavespeed_task_id:
                    continue
                    
                try:
                    # Get job status from WaveSpeed
                    wavespeed_result = await wavespeed_service.get_job_result(wavespeed_task_id)
                    task_data = wavespeed_result.get('data', {})
                    
                    # Get new status and outputs
                    new_status = task_data.get('status', job.status)
                    outputs = task_data.get('outputs', [])
                    error_message = task_data.get('error')
                    
                    # Map WaveSpeed status to our status
                    status_map = {
                        "created": "pending",
                        "processing": "running",
                        "completed": "completed",
                        "failed": "failed"
                    }
                    mapped_status = status_map.get(new_status, new_status)
                    
                    # Determine if we need to update
                    should_commit = False
                    
                    if mapped_status != job.status:
                        job.status = mapped_status
                        should_commit = True
                        
                    if outputs:
                        output_url = None
                        if isinstance(outputs, list) and len(outputs) > 0:
                            output_url = outputs[0]
                        elif isinstance(outputs, str):
                            output_url = outputs
                        
                        if output_url and output_url != job.output_url:
                            job.output_url = output_url
                            should_commit = True
                            
                    if error_message and error_message != job.error_message:
                        job.error_message = error_message
                        should_commit = True
                        
                    if should_commit:
                        job.updated_at = datetime.utcnow()
                        
                        # If newly completed, deduct credits
                        if mapped_status == "completed" and job.actual_credit_cost == 0:
                            actual_cost = job.estimated_credit_cost
                            job.actual_credit_cost = actual_cost
                            
                            # Deduct credits
                            credits_service = CreditsService(session)
                            # We need to await this within the loop
                            await credits_service.spend_credits(
                                user_id=job.user_id,
                                amount=actual_cost,
                                reason="background_job_completion",
                                metadata={"job_id": str(job.id), "task_id": wavespeed_task_id}
                            )
                            logger.info(f"Background: Deducted {actual_cost} credits for job {job.id}")
                        
                        session.add(job)
                        await session.commit()
                        updated_count += 1
                        logger.info(f"Background: Updated job {job.id} status to {mapped_status}")
                        
                except Exception as e:
                    logger.warning(f"Background: Failed to check status for job {job.id}: {e}")
                    continue
            
            if updated_count > 0:
                logger.info(f"Background job check completed. Updated {updated_count} jobs.")
                
        except Exception as e:
            logger.error(f"Error in background active jobs check: {e}", exc_info=True)
            await session.rollback()


def setup_scheduler() -> AsyncIOScheduler:
    """Set up and configure the APScheduler."""
    global scheduler
    
    scheduler = AsyncIOScheduler()
    
    # Schedule credit reset to run daily at 2:00 AM
    # This checks all subscriptions and resets credits for yearly plans monthly
    scheduler.add_job(
        reset_monthly_credits_task,
        trigger=CronTrigger(hour=2, minute=0),  # Daily at 2:00 AM
        id="reset_monthly_credits",
        name="Reset Monthly Credits for Subscriptions",
        replace_existing=True,
        max_instances=1,  # Only one instance can run at a time
        coalesce=True,  # If multiple runs are missed, only run once
    )
    
    # Schedule active job status check to run every 10 seconds
    # This ensures jobs update even if the user closes the browser
    scheduler.add_job(
        check_active_jobs_task,
        trigger=IntervalTrigger(seconds=10),
        id="check_active_jobs",
        name="Check Active Job Statuses",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    
    logger.info("Scheduler configured: Credit reset task scheduled daily at 2:00 AM")
    logger.info("Scheduler configured: Active job check scheduled every 10 seconds")
    return scheduler


@asynccontextmanager
async def lifespan(app) -> AsyncGenerator:
    """
    FastAPI lifespan context manager.
    Starts the scheduler and Redis when the app starts and stops them when the app shuts down.
    """
    global scheduler
    
    # Startup: Initialize Redis
    from app.services.redis_service import redis_service
    logger.info("Initializing Redis...")
    await redis_service.initialize()
    
    # Startup: Start the scheduler
    logger.info("Starting background scheduler...")
    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("Background scheduler started successfully")
    
    yield
    
    # Shutdown: Stop the scheduler
    logger.info("Shutting down background scheduler...")
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=True)
    logger.info("Background scheduler stopped")
    
    # Shutdown: Close Redis connection
    logger.info("Closing Redis connection...")
    await redis_service.close()
    logger.info("Redis connection closed")


def get_scheduler() -> AsyncIOScheduler:
    """Get the global scheduler instance."""
    return scheduler

