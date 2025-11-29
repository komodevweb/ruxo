import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr

class UserProfileBase(BaseModel):
    email: EmailStr
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None

class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None

class UserProfileRead(UserProfileBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

class UserMe(UserProfileRead):
    # Include subscription and credits info in the detailed "me" response
    plan_name: Optional[str] = None
    plan_interval: Optional[str] = None  # 'month' or 'year'
    subscription_status: Optional[str] = None # 'active', 'trialing', 'canceled', etc.
    credit_balance: int = 0
    credits_per_month: Optional[int] = None  # Credits provided by the plan

