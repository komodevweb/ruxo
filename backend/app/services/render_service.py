import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.render import RenderJob, Asset
from app.schemas.render import RenderJobCreate
from app.services.credits_service import CreditsService
from app.services.ai_providers.mock_provider import MockAIProvider

class RenderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.credits_service = CreditsService(session)
        self.providers = {"mock": MockAIProvider()}

    async def create_job(self, user_id: uuid.UUID, job_data: RenderJobCreate) -> RenderJob:
        provider = self.providers.get(job_data.provider, self.providers["mock"])
        cost = await provider.estimate_credits(job_data.job_type, job_data.settings)
        
        # Deduct credits
        await self.credits_service.spend_credits(user_id, cost, "render_job", {"job_type": job_data.job_type})
        
        job = RenderJob(
            user_id=user_id,
            job_type=job_data.job_type,
            provider=job_data.provider,
            input_prompt=job_data.input_prompt,
            settings=job_data.settings,
            estimated_credit_cost=cost,
            status="pending"
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        
        # Submit job (async in background in real app)
        await provider.submit_job(job)
        
        return job

    async def get_job(self, job_id: uuid.UUID, user_id: uuid.UUID) -> RenderJob:
        result = await self.session.execute(select(RenderJob).where(RenderJob.id == job_id, RenderJob.user_id == user_id))
        return result.scalar_one_or_none()

