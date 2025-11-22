import uuid
from typing import Optional, Dict, Any
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.logging import AuditLog
from app.core.config import settings

async def log_audit_event(
    session: AsyncSession,
    action: str,
    user_id: Optional[uuid.UUID] = None,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
):
    """Log an audit event to the database."""
    if not settings.ENABLE_AUDIT_LOGGING:
        return
    
    ip_address = None
    if request:
        # Extract IP from request
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip_address = forwarded.split(",")[0].strip()
        else:
            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                ip_address = real_ip
            elif request.client:
                ip_address = request.client.host
    
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        details=details or {},
        ip_address=ip_address
    )
    
    session.add(audit_log)
    await session.commit()

