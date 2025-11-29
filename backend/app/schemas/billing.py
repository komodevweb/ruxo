from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class CheckoutSessionCreate(BaseModel):
    plan_name: str  # e.g., "starter_monthly", "pro_yearly", "creator_monthly", "ultimate_monthly"
    skip_trial: bool = False  # If True, skip trial period and subscribe immediately

class CheckoutSessionResponse(BaseModel):
    url: str

class PortalSessionResponse(BaseModel):
    url: str

class SubscriptionStatus(BaseModel):
    plan_name: Optional[str]
    status: Optional[str]
    current_period_end: Optional[datetime]
    credit_balance: int

