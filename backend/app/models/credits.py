import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, func

class CreditWallet(SQLModel, table=True):
    __tablename__ = "credit_wallets"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user_profiles.id", index=True, unique=True)
    
    balance_credits: int = Field(default=0)
    lifetime_credits_added: int = Field(default=0)
    lifetime_credits_spent: int = Field(default=0)
    
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    )

class CreditTransaction(SQLModel, table=True):
    __tablename__ = "credit_transactions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user_profiles.id", index=True)
    
    amount: int
    direction: str # credit, debit
    reason: str # subscription_renewal, topup, render_job, refund
    metadata_json: Optional[str] = None # JSON string for extra details
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

