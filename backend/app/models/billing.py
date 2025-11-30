import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, func

class Plan(SQLModel, table=True):
    __tablename__ = "plans"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(unique=True, index=True) # e.g. "starter_monthly", "starter_yearly"
    display_name: str # e.g. "Starter Monthly"
    
    stripe_price_id: str # The Stripe Price ID
    credits_per_month: int # Credits provided per month (e.g., 200)
    
    interval: str # month, year
    amount_cents: int # price in cents for display
    currency: str = "usd"
    
    # Trial period configuration
    trial_days: int = Field(default=3) # Trial period in days (default 3 days)
    trial_amount_cents: int = Field(default=100) # Trial price in cents (default $1.00)
    trial_credits: int = Field(default=70) # Credits during trial period (default 70)
    
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Subscription(SQLModel, table=True):
    __tablename__ = "subscriptions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user_profiles.id", index=True)
    plan_id: Optional[uuid.UUID] = Field(foreign_key="plans.id", nullable=True)
    
    stripe_customer_id: str = Field(index=True)
    stripe_subscription_id: str = Field(index=True, unique=True)
    plan_name: str # Storing the name for historical reference or easy access
    status: str  # active, canceled, trialing, past_due, etc.
    
    current_period_start: datetime
    current_period_end: datetime
    last_credit_reset: Optional[datetime] = None # Track when credits were last reset
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,  # Python default as fallback
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    )

class Payment(SQLModel, table=True):
    __tablename__ = "payments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user_profiles.id", index=True)
    
    stripe_payment_intent_id: Optional[str] = Field(default=None, index=True)
    stripe_checkout_session_id: Optional[str] = Field(default=None, index=True)
    
    amount: int # in cents
    currency: str = "usd"
    type: str # subscription, topup
    status: str
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
