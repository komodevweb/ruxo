import uuid
from datetime import datetime
from typing import Optional, Any
from sqlmodel import SQLModel, Field, JSON
from sqlalchemy import Column, DateTime, func

class RenderJob(SQLModel, table=True):
    __tablename__ = "render_jobs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user_profiles.id", index=True)
    
    job_type: str # image, video
    provider: str # sora, veo, kling, wan, mock
    
    input_prompt: str # or JSON if complex
    settings: dict = Field(default={}, sa_column=Column(JSON))
    
    status: str # pending, queued, running, completed, failed, canceled
    
    estimated_credit_cost: int = 0
    actual_credit_cost: int = 0
    
    output_url: Optional[str] = None
    error_message: Optional[str] = None
    
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    )

class Asset(SQLModel, table=True):
    __tablename__ = "assets"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user_profiles.id", index=True)
    render_job_id: Optional[uuid.UUID] = Field(foreign_key="render_jobs.id", default=None)
    
    asset_type: str # image, video
    url: str
    thumbnail_url: Optional[str] = None
    
    meta_data: dict = Field(default={}, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

