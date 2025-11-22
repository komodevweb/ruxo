import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel

class RenderJobCreate(BaseModel):
    job_type: str # image, video
    input_prompt: str
    settings: Dict[str, Any] = {}
    provider: str = "mock"

class RenderJobRead(BaseModel):
    id: uuid.UUID
    job_type: str
    provider: str
    status: str
    output_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

class AssetRead(BaseModel):
    id: uuid.UUID
    asset_type: str
    url: str
    thumbnail_url: Optional[str] = None
    created_at: datetime

