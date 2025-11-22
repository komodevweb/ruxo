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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

from app.db.session import engine
from app.models.billing import Subscription
from app.services.billing_service import BillingService
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession as AsyncSessionType

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
    
    logger.info("Scheduler configured: Credit reset task scheduled daily at 2:00 AM")
    return scheduler


@asynccontextmanager
async def lifespan(app) -> AsyncGenerator:
    """
    FastAPI lifespan context manager.
    Starts the scheduler when the app starts and stops it when the app shuts down.
    """
    global scheduler
    
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


def get_scheduler() -> AsyncIOScheduler:
    """Get the global scheduler instance."""
    return scheduler

