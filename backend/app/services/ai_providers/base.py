from typing import Protocol, runtime_checkable, Dict, Any
from app.models.render import RenderJob

@runtime_checkable
class BaseAIProvider(Protocol):
    async def estimate_credits(self, job_type: str, settings: Dict[str, Any]) -> int:
        ...

    async def submit_job(self, render_job: RenderJob) -> None:
        ...

    async def poll_status(self, render_job: RenderJob) -> None:
        ...

