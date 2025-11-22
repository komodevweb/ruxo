import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, JSON
from sqlalchemy import Column, DateTime, func

class WebhookEventLog(SQLModel, table=True):
    __tablename__ = "webhook_event_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    source: str # stripe, etc.
    event_id: str
    event_type: str
    payload: dict = Field(default={}, sa_column=Column(JSON))
    status: str # processed, failed
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: Optional[uuid.UUID] = Field(foreign_key="user_profiles.id", nullable=True)
    action: str
    details: dict = Field(default={}, sa_column=Column(JSON))
    ip_address: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CountryIP(SQLModel, table=True):
    __tablename__ = "country_ips"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    ip_address: str = Field(index=True, unique=True)
    country_code: str
    country_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

