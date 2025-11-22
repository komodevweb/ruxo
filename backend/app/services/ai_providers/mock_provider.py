import asyncio
from typing import Dict, Any
from app.models.render import RenderJob
from app.services.ai_providers.base import BaseAIProvider

class MockAIProvider:
    async def estimate_credits(self, job_type: str, settings: Dict[str, Any]) -> int:
        return 10  # Fixed cost for mock

    async def submit_job(self, render_job: RenderJob) -> None:
        # Simulate API call
        await asyncio.sleep(1)
        print(f"Mock job submitted: {render_job.id}")

    async def poll_status(self, render_job: RenderJob) -> None:
        # Simulate completion
        render_job.status = "completed"
        render_job.output_url = "https://placehold.co/600x400.png"
        render_job.actual_credit_cost = 10

