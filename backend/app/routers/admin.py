from typing import List
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.common import StandardResponse
from app.models.logging import AuditLog, WebhookEventLog
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import UserProfile
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter()

def get_admin_user(current_user: UserProfile = Depends(get_current_user)) -> UserProfile:
    """Verify that the current user is an admin."""
    admin_emails = [email.strip() for email in settings.ADMIN_EMAILS.split(",") if email.strip()]
    
    if not admin_emails:
        # If no admin emails configured, deny access
        raise HTTPException(status_code=403, detail="Admin access not configured")
    
    if current_user.email not in admin_emails and current_user.email != settings.SUPER_ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Not authorized: Admin access required")
    
    return current_user

@router.get("/logs/webhooks", response_model=List[WebhookEventLog])
async def get_webhook_logs(
    skip: int = 0, 
    limit: int = 100,
    admin: UserProfile = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(WebhookEventLog).offset(skip).limit(limit).order_by(WebhookEventLog.created_at.desc()))
    return result.scalars().all()

@router.get("/logs/audit", response_model=List[AuditLog])
async def get_audit_logs(
    skip: int = 0, 
    limit: int = 100,
    admin: UserProfile = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(AuditLog).offset(skip).limit(limit).order_by(AuditLog.created_at.desc()))
    return result.scalars().all()

@router.post("/test/credit-reset")
async def test_credit_reset(
    admin: UserProfile = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Manually trigger credit reset task for testing.
    Only available to admins.
    """
    from app.services.scheduler_service import reset_monthly_credits_task
    
    try:
        await reset_monthly_credits_task()
        return {"status": "success", "message": "Credit reset task completed. Check logs for details."}
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in manual credit reset: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error running credit reset: {str(e)}")