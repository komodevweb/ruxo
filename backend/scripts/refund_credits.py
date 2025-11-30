import asyncio
import sys
import uuid
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import AsyncSession as AsyncSessionType
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from app.db.session import engine
from app.models.user import UserProfile
from app.services.credits_service import CreditsService

async def refund_credits(user_id_str: str, amount: int, reason: str = "refund"):
    """Refund credits to a user."""
    async_session = sessionmaker(engine, class_=AsyncSessionType, expire_on_commit=False)
    async with async_session() as session:
        try:
            # Parse user ID
            try:
                user_id = uuid.UUID(user_id_str)
            except ValueError:
                print(f"❌ Invalid user ID format: {user_id_str}")
                return
            
            # Find user
            result = await session.execute(
                select(UserProfile).where(UserProfile.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"❌ User not found: {user_id}")
                return
            
            print(f"✓ Found user: {user.email} ({user.id})")
            
            # Refund credits
            credits_service = CreditsService(session)
            wallet = await credits_service.get_wallet(user.id)
            old_balance = wallet.balance_credits
            
            print(f"💰 Current balance: {old_balance}")
            print(f"➕ Refunding: {amount} credits")
            
            await credits_service.add_credits(
                user_id=user.id,
                amount=amount,
                reason=reason,
                metadata={"refund_type": "duplicate_charge_correction"}
            )
            
            # Refresh wallet to confirm
            wallet = await credits_service.get_wallet(user.id)
            new_balance = wallet.balance_credits
            
            print(f"✅ Refund successful!")
            print(f"💰 New balance: {new_balance}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/refund_credits.py <user_id> <amount> [reason]")
        sys.exit(1)
    
    user_id = sys.argv[1]
    amount = int(sys.argv[2])
    reason = sys.argv[3] if len(sys.argv) > 3 else "refund_duplicate_charge"
    
    asyncio.run(refund_credits(user_id, amount, reason))

