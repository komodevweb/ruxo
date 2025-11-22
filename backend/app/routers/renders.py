import uuid
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.render import RenderJobCreate, RenderJobRead
from app.core.security import get_current_user
from app.models.user import UserProfile
from app.services.render_service import RenderService
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.post("/", response_model=RenderJobRead)
async def create_render_job(
    job_data: RenderJobCreate,
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    service = RenderService(session)
    job = await service.create_job(current_user.id, job_data)
    return job

@router.get("/{job_id}", response_model=RenderJobRead)
async def get_render_job(
    job_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    service = RenderService(session)
    job = await service.get_job(job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

