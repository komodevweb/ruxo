from datetime import datetime
from pydantic import BaseModel

class CreditBalance(BaseModel):
    balance: int
    lifetime_used: int
    last_updated: datetime

class CreditTopupRequest(BaseModel):
    credits_to_purchase: int

