import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, func

class UserProfile(SQLModel, table=True):
    __tablename__ = "user_profiles"

    id: uuid.UUID = Field(default=None, primary_key=True) # Matches Supabase auth.users.id
    email: str = Field(index=True, unique=True)
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    
    # Tracking context for Facebook Conversions API (stored at signup, used at email verification)
    signup_ip: Optional[str] = None
    signup_user_agent: Optional[str] = None
    signup_fbp: Optional[str] = None  # Facebook browser ID cookie
    signup_fbc: Optional[str] = None  # Facebook click ID cookie
    
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    )

class ApiKey(SQLModel, table=True):
    __tablename__ = "api_keys"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user_profiles.id", index=True)
    key_hash: str
    name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

class PasswordResetCode(SQLModel, table=True):
    __tablename__ = "password_reset_codes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(index=True)
    code: str = Field(index=True)
    used: bool = Field(default=False, index=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    expires_at: datetime = Field(nullable=False)

